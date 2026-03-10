"""
LexFlow — Billing Intelligence Platform

Converts voice dictations into structured billing entries for legal professionals
using Google Gemini AI. Supabase handles auth (JWT) and data (Postgres + RLS).

Author: Tshepiso Jafta
Version: 4.0 — WhatsApp integration
"""

# ── stdlib ──────────────────────────────────────────────────────────
import os
import csv
import io
import json
import shutil
import tempfile
import time
import asyncio

# ── third-party ─────────────────────────────────────────────────────
import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel


# ====================================================================
# 1. CONFIGURATION — loaded once at startup
# ====================================================================

load_dotenv()

API_KEY              = os.getenv("GOOGLE_API_KEY")
MODEL_NAME           = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

FRONTEND_DIST      = os.path.join(os.path.dirname(__file__), "frontend", "dist")
ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}
MAX_RETRIES        = 3          # Gemini 429 retry attempts
RETRY_BASE_DELAY   = 5          # seconds — doubles each attempt
DEMO_EMAIL         = "demo@lexflow.app"
DEFAULT_RATE       = 2500       # ZAR/hr fallback when profile has no rate
HTTP_TIMEOUT       = 15.0       # seconds for all Supabase REST calls

# WhatsApp Cloud API
WHATSAPP_TOKEN      = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID   = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "lexflow-verify-2026")
GRAPH_API_URL       = "https://graph.facebook.com/v21.0"

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not set — /transcribe will fail.")
if not SUPABASE_URL:
    print("WARNING: SUPABASE_URL not set — all DB calls will fail.")


# ====================================================================
# 2. SUPABASE HELPERS — thin wrappers for REST URLs and auth headers
# ====================================================================

def _rest_url(path: str) -> str:
    """Full Supabase REST endpoint, e.g. 'billing_entries?...'"""
    return f"{SUPABASE_URL}/rest/v1/{path}"


def _auth_url(path: str) -> str:
    """Full Supabase Auth endpoint, e.g. 'user'"""
    return f"{SUPABASE_URL}/auth/v1/{path}"


def _headers(token: str | None = None) -> dict:
    """Standard headers — apikey is always the service key,
    but Authorization uses the user's JWT so RLS applies."""
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {token or SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def _service_headers() -> dict:
    """Headers that bypass RLS — only for admin ops like demo wipe."""
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


# ====================================================================
# 3. AUTH DEPENDENCY — extracts + validates JWT on every request
# ====================================================================

async def get_current_user(request: Request) -> dict:
    """Verify Bearer token against Supabase Auth; return user dict or raise 401."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")

    token = auth.removeprefix("Bearer ")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            _auth_url("user"),
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {token}"},
        )

    if res.status_code != 200:
        raise HTTPException(401, "Invalid or expired token")
    return {**res.json(), "token": token}


# ====================================================================
# 4. SCHEMA — Pydantic model for Gemini structured output
# ====================================================================

class BillingEntry(BaseModel):
    client_name: str
    matter_description: str
    duration: str
    billable_amount: str


class TranscriptionResult(BaseModel):
    """Wrapper for multi-matter extraction + AI confidence score."""
    entries: list[BillingEntry]
    confidence: float  # 0.0-1.0 — how confident the AI is in its extraction


# ====================================================================
# 5. GEMINI — retry logic + prompt builder
# ====================================================================

def _extract_billing(client: genai.Client, audio_ref, model: str, prompt: str) -> TranscriptionResult:
    """Call Gemini with structured output. Returns multiple entries + confidence.
    Retries on 429 with exponential backoff.

    WARNING: This function uses blocking time.sleep() for retry delays.
    It MUST be called via asyncio.to_thread() - never directly from async context."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[audio_ref, prompt],
                config={"response_mime_type": "application/json", "response_schema": TranscriptionResult},
            )
            # Gemini returns parsed Pydantic when possible; fall back to raw JSON
            if response.parsed:
                return response.parsed
            return TranscriptionResult(**json.loads(response.text))

        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" not in msg and "quota" not in msg:
                raise  # not a rate-limit — propagate immediately
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[GEMINI] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
            time.sleep(delay)  # safe: runs in asyncio.to_thread

    raise HTTPException(429, f"Gemini rate limit after {MAX_RETRIES} retries: {last_err}")


def _build_prompt(hourly_rate: int) -> str:
    """Assemble the billing-extraction prompt with the attorney's ZAR rate.
    Supports multi-matter: if the voice note covers multiple clients/matters,
    each gets its own entry in the entries array."""
    return (
        "You are a legal billing assistant. Listen to this voice note from a "
        "lawyer describing work they did.\n\n"
        "IMPORTANT: The voice note may describe work for MULTIPLE clients or matters. "
        "If so, create a SEPARATE entry for each distinct client/matter.\n\n"
        "For each entry, extract:\n"
        "- client_name: The client or party name. Use 'Unspecified Client' if none.\n"
        "- matter_description: Concise summary of the legal work.\n"
        "- duration: Duration of the LEGAL WORK (not recording length). "
        "Look for references like 'spent 2 hours', 'took 45 minutes'. "
        "If unspecified, estimate by complexity. Format as '2 hours' or '45 minutes'.\n"
        f"- billable_amount: Calculate using rate R{hourly_rate}/hr. "
        f"Example: 2 hours = 'R{hourly_rate * 2}', 30 min = 'R{hourly_rate // 2}'.\n\n"
        "Also provide a 'confidence' score (0.0 to 1.0) indicating how confident you "
        "are in the overall extraction accuracy. Lower confidence if audio is unclear, "
        "names are ambiguous, or durations are estimated.\n\n"
        "Return valid JSON matching the schema. Every field must be non-empty."
    )


async def _get_hourly_rate(user: dict) -> int:
    """Fetch attorney's hourly rate from profile. Returns DEFAULT_RATE if missing."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            _rest_url(f"profiles?id=eq.{user['id']}&select=hourly_rate"),
            headers=_headers(user["token"]),
        )
    if res.status_code != 200 or not res.json():
        return DEFAULT_RATE
    return res.json()[0].get("hourly_rate", DEFAULT_RATE)


# ====================================================================
# 6. APP SETUP
# ====================================================================

app = FastAPI(title="LexFlow API", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173", "https://lexflow-dwa0.onrender.com"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ====================================================================
# 7. ENDPOINTS — grouped by domain
# ====================================================================

# ── Transcription (core AI feature) ────────────────────────────────

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload audio -> Gemini extracts billing fields -> return for HITL review."""
    if not API_KEY:
        raise HTTPException(500, "Server misconfigured: missing GOOGLE_API_KEY")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'")

    hourly_rate = await _get_hourly_rate(user)
    gemini = genai.Client(api_key=API_KEY)
    tmp_path = None
    uploaded = None

    try:
        # Save to temp file (Gemini SDK requires a path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        uploaded = await asyncio.to_thread(gemini.files.upload, file=tmp_path)
        result = await asyncio.to_thread(_extract_billing, gemini, uploaded, MODEL_NAME, _build_prompt(hourly_rate))

        print(f"[GEMINI] rate={hourly_rate}, entries={len(result.entries)}, confidence={result.confidence}")
        return JSONResponse(content=result.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        # Log full error server-side, send sanitized message to client
        print(f"[ERROR] Transcription failed: {e}")
        raise HTTPException(500, "Audio processing failed. Please try again or contact support.")
    finally:
        # POPIA: scrub temp file + Gemini upload immediately
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if uploaded:
            try:
                gemini.files.delete(name=uploaded.name)
                print(f"[POPIA] Deleted Gemini upload: {uploaded.name}")
            except Exception:
                pass


# ── Billing CRUD ────────────────────────────────────────────────────

@app.post("/billing")
async def save_billing_entry(request: Request, user: dict = Depends(get_current_user)):
    """Save a user-approved billing entry (HITL approve action).
    Stores both the approved data and the original AI output for audit trail."""
    body = await request.json()
    required = {"client_name", "matter_description", "duration", "billable_amount"}
    missing = required - set(body.keys())
    if missing:
        raise HTTPException(400, f"Missing fields: {missing}")

    # Build the row (original_ai_output is kept client-side until the DB column is added)
    # Input validation
    for field in required:
        val = str(body[field])
        if len(val) > 2000:
            raise HTTPException(400, f"Field '{field}' exceeds maximum length (2000 chars)")
        if len(val.strip()) == 0:
            raise HTTPException(400, f"Field '{field}' cannot be empty")

    row = {"user_id": user["id"], **{k: body[k] for k in required}}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.post(
            _rest_url("billing_entries"),
            headers=_headers(user["token"]),
            json=row,
        )
    if res.status_code not in (200, 201):
        raise HTTPException(500, f"Failed to save: {res.text}")
    return JSONResponse(content={"status": "saved"}, status_code=201)


@app.get("/billing")
async def get_billing(user: dict = Depends(get_current_user)):
    """Return all billing entries for the authenticated user (RLS-enforced)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            _rest_url("billing_entries?select=*&order=created_at.desc"),
            headers=_headers(user["token"]),
        )
    if res.status_code != 200:
        return JSONResponse(content={"count": 0, "entries": []})
    entries = res.json()
    return JSONResponse(content={"count": len(entries), "entries": entries})


@app.get("/billing/csv")
async def download_csv(user: dict = Depends(get_current_user)):
    """Export billing entries as a downloadable CSV file."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            _rest_url("billing_entries?select=*&order=created_at.desc"),
            headers=_headers(user["token"]),
        )
    entries = res.json() if res.status_code == 200 else []

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "Timestamp", "Client Name", "Matter Description", "Duration", "Billable Amount",
    ])
    writer.writeheader()
    for e in entries:
        writer.writerow({
            "Timestamp":          e.get("created_at", ""),
            "Client Name":        e.get("client_name", ""),
            "Matter Description": e.get("matter_description", ""),
            "Duration":           e.get("duration", ""),
            "Billable Amount":    e.get("billable_amount", ""),
        })
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=billing.csv"},
    )


# ── Profile ─────────────────────────────────────────────────────────

@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile row."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            _rest_url(f"profiles?id=eq.{user['id']}&select=*"),
            headers=_headers(user["token"]),
        )
    if res.status_code == 200 and res.json():
        return JSONResponse(content=res.json()[0])
    raise HTTPException(404, "Profile not found")


@app.patch("/profile")
async def update_profile(request: Request, user: dict = Depends(get_current_user)):
    """Update profile fields (onboarding, rate changes). Whitelist-filtered."""
    body = await request.json()
    allowed = {"full_name", "firm_name", "phone", "hourly_rate", "onboarded"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(400, "No valid fields to update")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.patch(
            _rest_url(f"profiles?id=eq.{user['id']}"),
            headers=_headers(user["token"]),
            json=update,
        )
    if res.status_code not in (200, 204):
        raise HTTPException(500, f"Failed to update profile: {res.text}")
    try:
        data = res.json() if res.text else None
        if data:
            return JSONResponse(content=data[0])
    except (ValueError, IndexError):
        pass
    return JSONResponse(content={"status": "updated"})



@app.delete("/billing/{entry_id}")
async def delete_billing_entry(entry_id: str, user: dict = Depends(get_current_user)):
    """Delete a specific billing entry by ID (must belong to authenticated user)."""
    headers = _headers(user["token"])
    headers["Prefer"] = "return=representation"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.delete(
            _rest_url(f"billing_entries?id=eq.{entry_id}&user_id=eq.{user['id']}"),
            headers=headers,
        )
    if res.status_code not in (200, 204):
        raise HTTPException(500, "Failed to delete entry")
    # Verify that a row was actually deleted
    deleted_rows = res.json() if res.text.strip() else []
    if not deleted_rows:
        raise HTTPException(404, "Entry not found or access denied")
    return JSONResponse(content={"status": "deleted"})


# ── Demo Seeder ─────────────────────────────────────────────────────

DEMO_ENTRIES = [
    {"client_name": "Ndlovu Holdings (Pty) Ltd",
     "matter_description": "Reviewed and advised on commercial lease agreement for new Sandton office premises. Identified non-standard escalation clauses and recommended amendments.",
     "duration": "2 hours", "billable_amount": "R5000"},
    {"client_name": "John Mokoena",
     "matter_description": "Consultation regarding unfair dismissal claim under the LRA. Drafted referral to CCMA and prepared initial statement of case.",
     "duration": "1.5 hours", "billable_amount": "R3750"},
    {"client_name": "Vukani Construction",
     "matter_description": "Reviewed BBBEE compliance documentation and shareholding structure. Provided written opinion on fronting risk under the Codes of Good Practice.",
     "duration": "3 hours", "billable_amount": "R7500"},
    {"client_name": "Sarah van der Merwe",
     "matter_description": "Drafted antenuptial contract with accrual system. Discussed implications of matrimonial property regime and estate planning considerations.",
     "duration": "1 hour", "billable_amount": "R2500"},
    {"client_name": "TechBridge Solutions",
     "matter_description": "Negotiated and finalized SLA terms for cloud infrastructure agreement. Reviewed data protection clauses for POPIA compliance.",
     "duration": "2.5 hours", "billable_amount": "R6250"},
]


@app.post("/demo/seed")
async def seed_demo_data(user: dict = Depends(get_current_user)):
    """Wipe and re-seed the demo account with fresh sample billing data."""
    # Guard: only the demo account may call this
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        auth_res = await client.get(
            _auth_url("user"),
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {user['token']}"},
        )
    if auth_res.status_code != 200:
        raise HTTPException(403, "Could not verify user")
    if auth_res.json().get("email", "") != DEMO_EMAIL:
        raise HTTPException(403, "Demo seed is only for demo accounts")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Delete old entries — service key bypasses RLS
        del_res = await client.delete(
            _rest_url(f"billing_entries?user_id=eq.{user['id']}"),
            headers=_service_headers(),
        )
        print(f"[DEMO] Deleted old entries: {del_res.status_code}")
        # Insert fresh entries under user's JWT
        for entry in DEMO_ENTRIES:
            await client.post(
                _rest_url("billing_entries"),
                headers=_headers(user["token"]),
                json={"user_id": user["id"], **entry},
            )
    return JSONResponse(content={"status": "demo_seeded", "entries": len(DEMO_ENTRIES)})




# ====================================================================
# 7B. WHATSAPP — voice note intake via Meta Cloud API
# ====================================================================

# ── WhatsApp helpers ────────────────────────────────────────────────

async def _wa_send(phone: str, text: str):
    """Send a WhatsApp text message via Cloud API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print("[WA] WhatsApp not configured — skipping send")
        return
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        await client.post(
            f"{GRAPH_API_URL}/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text},
            },
        )


async def _wa_download_audio(media_id: str) -> str | None:
    """Download a WhatsApp voice note to a temp file. Returns path or None."""
    if not WHATSAPP_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get download URL from media ID
        meta = await client.get(
            f"{GRAPH_API_URL}/{media_id}",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        )
        if meta.status_code != 200:
            print(f"[WA] Failed to get media URL: {meta.status_code}")
            return None
        dl_url = meta.json().get("url")
        if not dl_url:
            return None

        # Step 2: Download the actual audio
        audio = await client.get(dl_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"})
        if audio.status_code != 200:
            print(f"[WA] Failed to download audio: {audio.status_code}")
            return None

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            tmp.write(audio.content)
            return tmp.name


async def _wa_get_or_create_user(phone: str) -> dict:
    """Get or create a WhatsApp user record in Supabase."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Check if user exists
        res = await client.get(
            _rest_url(f"whatsapp_users?phone=eq.{phone}&select=*"),
            headers=_service_headers(),
        )
        rows = res.json() if res.status_code == 200 else []
        if rows:
            return rows[0]

        # Create new user
        import secrets
        link_code = secrets.token_urlsafe(6)[:8].upper()
        new_user = {"phone": phone, "state": "NEW", "hourly_rate": 2500, "link_code": link_code}
        res = await client.post(
            _rest_url("whatsapp_users"),
            headers=_service_headers(),
            json=new_user,
        )
        if res.status_code in (200, 201):
            return res.json()[0]
        print(f"[WA] Failed to create user: {res.status_code} {res.text}")
        return new_user


async def _wa_update_user(phone: str, updates: dict):
    """Update a WhatsApp user's state/rate/pending entry."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        await client.patch(
            _rest_url(f"whatsapp_users?phone=eq.{phone}"),
            headers=_service_headers(),
            json=updates,
        )


async def _wa_save_billing(wa_user: dict, entry_data: dict):
    """Save an approved WhatsApp billing entry to billing_entries."""
    user_id = wa_user.get("user_id")
    row = {
        "client_name": entry_data.get("client_name", "Unknown"),
        "matter_description": entry_data.get("matter_description", ""),
        "duration": entry_data.get("duration", "0h"),
        "billable_amount": entry_data.get("billable_amount", "R0"),
        "source": "whatsapp",
    }
    # Only set user_id if linked to a real Supabase auth account
    if user_id:
        row["user_id"] = user_id

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.post(
            _rest_url("billing_entries"),
            headers=_service_headers(),
            json=row,
        )
        if res.status_code not in (200, 201):
            print(f"[WA] Save failed: {res.status_code} {res.text}")
        return res.status_code in (200, 201)


async def _wa_process_voice_note(phone: str, media_id: str):
    """Background task: download audio → Gemini extract → reply with summary."""
    wa_user = await _wa_get_or_create_user(phone)
    hourly_rate = wa_user.get("hourly_rate", DEFAULT_RATE)

    await _wa_send(phone, "Processing your voice note...")

    tmp_path = await _wa_download_audio(media_id)
    if not tmp_path:
        await _wa_send(phone, "Could not download the voice note. Please try again.")
        return

    uploaded = None
    try:
        gemini = genai.Client(api_key=API_KEY)
        uploaded = await asyncio.to_thread(gemini.files.upload, file=tmp_path)
        result = await asyncio.to_thread(
            _extract_billing, gemini, uploaded, MODEL_NAME, _build_prompt(hourly_rate)
        )

        if not result.entries:
            await _wa_send(phone, "Could not extract billing data from that recording.\nTry again with a clearer voice note.")
            await _wa_update_user(phone, {"state": "READY"})
            return

        # Use first entry for approval flow
        entry = result.entries[0]
        summary = (
            f"*Billing Entry*\n"
            f"\n"
            f"Client: {entry.client_name}\n"
            f"Matter: {entry.matter_description}\n"
            f"Duration: {entry.duration}\n"
            f"Amount: {entry.billable_amount}\n"
            f"\n"
            f"Reply *YES* to save, *NO* to discard, or *EDIT* to modify on web."
        )
        await _wa_send(phone, summary)
        await _wa_update_user(phone, {
            "state": "AWAITING_APPROVAL",
            "pending_entry": entry.model_dump(),
        })

    except Exception as e:
        print(f"[WA] Processing failed for {phone}: {e}")
        await _wa_send(phone, "Something went wrong. Please try again.")
        await _wa_update_user(phone, {"state": "READY"})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if uploaded:
            try:
                await asyncio.to_thread(gemini.files.delete, name=uploaded.name)
            except Exception:
                pass


# ── WhatsApp webhook endpoints ──────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta sends this GET to verify the webhook URL during setup."""
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        print(f"[WA] Webhook verified")
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(403, "Webhook verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request, bg: BackgroundTasks):
    """Receive incoming WhatsApp messages. Must return 200 immediately."""
    body = await request.json()

    # Extract message data from Meta's nested payload
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])
    except (KeyError, IndexError):
        return {"status": "ok"}  # Not a message event — ignore

    for msg in messages:
        phone = msg.get("from", "")
        msg_type = msg.get("type", "")

        if msg_type == "audio":
            # Voice note received
            media_id = msg["audio"]["id"]
            wa_user = await _wa_get_or_create_user(phone)

            if wa_user["state"] == "NEW":
                # First interaction — send welcome, ask for rate
                welcome = (
                    "*LexFlow* — Billing Intelligence\n"
                    "\n"
                    "Turn voice notes into structured billing entries.\n"
                    "\n"
                    "_How it works:_\n"
                    "1. Send a voice note about your billable work\n"
                    "2. I extract the details automatically\n"
                    "3. You approve and it's saved\n"
                    "\n"
                    "To begin, reply with your hourly rate in ZAR.\n"
                    "Example: *3500*"
                )
                await _wa_send(phone, welcome)
                await _wa_update_user(phone, {"state": "AWAITING_RATE"})

            elif wa_user["state"] == "AWAITING_RATE":
                await _wa_send(phone, "Set your hourly rate first.\nReply with a number, e.g. *3500*")

            else:
                # READY or AWAITING_APPROVAL — process the voice note
                bg.add_task(_wa_process_voice_note, phone, media_id)

        elif msg_type == "text":
            text = msg.get("text", {}).get("body", "").strip()
            wa_user = await _wa_get_or_create_user(phone)

            if wa_user["state"] == "NEW":
                # First text message — send welcome
                welcome = (
                    "*LexFlow* — Billing Intelligence\n"
                    "\n"
                    "Turn voice notes into structured billing entries.\n"
                    "\n"
                    "_How it works:_\n"
                    "1. Send a voice note about your billable work\n"
                    "2. I extract the details automatically\n"
                    "3. You approve and it's saved\n"
                    "\n"
                    "To begin, reply with your hourly rate in ZAR.\n"
                    "Example: *3500*"
                )
                await _wa_send(phone, welcome)
                await _wa_update_user(phone, {"state": "AWAITING_RATE"})

            elif wa_user["state"] == "AWAITING_RATE":
                # Expecting a number
                cleaned = text.replace("R", "").replace("r", "").replace(",", "").replace(" ", "").strip()
                if cleaned.isdigit() and int(cleaned) > 0:
                    rate = int(cleaned)
                    await _wa_update_user(phone, {"hourly_rate": rate, "state": "READY"})
                    await _wa_send(phone, (
                        f"Rate set to *R{rate:,}/hr*.\n"
                        f"\n"
                        f"Send a voice note to get started.\n"
                        f"\n"
                        f"_Commands:_\n"
                        f"RATE \u2014 update hourly rate\n"
                        f"LINK \u2014 connect web dashboard\n"
                        f"HELP \u2014 show commands"
                    ))
                else:
                    await _wa_send(phone, "Reply with a valid number, e.g. *3500*")

            elif wa_user["state"] == "AWAITING_APPROVAL":
                upper = text.upper().strip()
                if upper == "YES":
                    pending = wa_user.get("pending_entry")
                    if pending:
                        ok = await _wa_save_billing(wa_user, pending)
                        if ok:
                            await _wa_send(phone, "Saved to your ledger.\nhttps://lexflow-dwa0.onrender.com")
                        else:
                            await _wa_send(phone, "Failed to save. Please try again.")
                    else:
                        await _wa_send(phone, "No pending entry. Send a new voice note.")
                    await _wa_update_user(phone, {"state": "READY", "pending_entry": None})

                elif upper == "NO":
                    await _wa_send(phone, "Entry discarded.")
                    await _wa_update_user(phone, {"state": "READY", "pending_entry": None})

                elif upper == "EDIT":
                    await _wa_send(phone, "Edit on web:\nhttps://lexflow-dwa0.onrender.com/review")
                    await _wa_update_user(phone, {"state": "READY"})

                else:
                    await _wa_send(phone, "Reply *YES* to save, *NO* to discard, or *EDIT* to modify on web.")

            elif wa_user["state"] == "READY":
                upper = text.upper().strip()

                if upper.startswith("RATE"):
                    parts = upper.replace("RATE", "").strip().replace("R", "").replace(",", "")
                    if parts.isdigit() and int(parts) > 0:
                        rate = int(parts)
                        await _wa_update_user(phone, {"hourly_rate": rate})
                        await _wa_send(phone, f"Rate updated to *R{rate:,}/hr*.")
                    else:
                        await _wa_send(phone, "Usage: *RATE 4000*")

                elif upper == "LINK":
                    code = wa_user.get("link_code", "N/A")
                    await _wa_send(phone, (
                        f"Link your WhatsApp to your web account:\n"
                        f"https://lexflow-dwa0.onrender.com/whatsapp/link/{code}\n"
                        f"\n"
                        f"Your link code: *{code}*"
                    ))

                elif upper == "HELP":
                    rate = wa_user.get("hourly_rate", DEFAULT_RATE)
                    await _wa_send(phone, (
                        f"*LexFlow Commands*\n"
                        f"\n"
                        f"Voice note \u2014 extract billing entry\n"
                        f"RATE [amount] \u2014 update rate (current: R{rate:,}/hr)\n"
                        f"LINK \u2014 connect to web dashboard\n"
                        f"HELP \u2014 show this list"
                        f"HELP — show this menu"
                    ))

                else:
                    await _wa_send(phone, "Send a voice note to extract billing, or type *HELP* for commands.")

    return {"status": "ok"}




@app.post("/whatsapp/link")
async def link_whatsapp(request: Request, user: dict = Depends(get_current_user)):
    """Link a WhatsApp number to a web account using a link code."""
    body = await request.json()
    code = body.get("code", "").strip().upper()
    if not code:
        raise HTTPException(400, "Missing link code")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Find WhatsApp user by link code
        res = await client.get(
            _rest_url(f"whatsapp_users?link_code=eq.{code}&select=*"),
            headers=_service_headers(),
        )
        rows = res.json() if res.status_code == 200 else []
        if not rows:
            raise HTTPException(404, "Invalid link code")

        wa_user = rows[0]
        if wa_user.get("user_id") and wa_user["user_id"] != user["id"]:
            raise HTTPException(409, "This WhatsApp number is already linked to another account")

        # Link: set user_id on whatsapp_users
        await client.patch(
            _rest_url(f"whatsapp_users?link_code=eq.{code}"),
            headers=_service_headers(),
            json={"user_id": user["id"]},
        )

        # Retroactively claim any unlinked WhatsApp billing entries from this phone
        phone = wa_user["phone"]
        # Find entries saved without user_id that came from this WhatsApp session
        unlinked = await client.get(
            _rest_url("billing_entries?user_id=is.null&source=eq.whatsapp&select=id"),
            headers=_service_headers(),
        )
        if unlinked.status_code == 200 and unlinked.json():
            for entry in unlinked.json():
                await client.patch(
                    _rest_url(f"billing_entries?id=eq.{entry['id']}"),
                    headers=_service_headers(),
                    json={"user_id": user["id"]},
                )

    return JSONResponse(content={"status": "linked", "phone": wa_user["phone"]})

# ====================================================================
# 8. STATIC FRONTEND SERVING — catch-all, registered LAST
# ====================================================================

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_frontend(full_path: str):
        index = os.path.join(FRONTEND_DIST, "index.html")
        if not os.path.isfile(index):
            return "Frontend build not found."
        with open(index, "r", encoding="utf-8") as f:
            return f.read()
else:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return "LexFlow API running. Frontend build (frontend/dist) not found."


# ====================================================================
# 9. ENTRYPOINT
# ====================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


