"""
LexFlow — Billing Intelligence Platform

Converts attorney voice dictations into structured billing entries
using Google Gemini AI. Supabase handles auth (JWT) and data (Postgres + RLS).

Author: Tshepiso Jafta
Version: 3.1
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
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
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
    Retries on 429 with exponential backoff."""
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
    return JSONResponse(content={"status": "saved"})


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
    if res.text and res.json():
        return JSONResponse(content=res.json()[0])
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


