"""
WhatsApp Cloud API integration — voice note intake, state machine, replies.

State machine per phone number:
  NEW → AWAITING_RATE → READY ↔ AWAITING_APPROVAL
"""
import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as _q

import httpx
from google import genai

from config import (
    API_KEY,
    APP_ENV,
    APP_URL,
    DEFAULT_RATE,
    GRAPH_API_URL,
    HTTP_TIMEOUT,
    MODEL_NAME,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_ID,
    WHATSAPP_TOKEN,
)
from services.gemini import build_prompt, extract_billing
from services.supabase import rest_url, service_headers

log = logging.getLogger("lexflow.whatsapp")

try:
    from services.vector_store import VectorStore
    _VECTOR_STORE: "VectorStore | None" = VectorStore()
except Exception as e:  # missing key, cold disk, etc. — RAG is optional
    _VECTOR_STORE = None
    log.info("Vector store unavailable (%s) — WhatsApp runs without policy context", e)


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify Meta webhook payload using HMAC-SHA256 and the app secret.

    Fails CLOSED in production when the secret is missing; only development
    skips verification.
    """
    if not WHATSAPP_APP_SECRET:
        if APP_ENV == "production":
            log.error("WHATSAPP_APP_SECRET missing in production — rejecting webhook")
            return False
        return True  # dev mode
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


# ── Messaging ────────────────────────────────────────────────────────────────

async def wa_send(phone: str, text: str) -> None:
    """Send a WhatsApp text message via Cloud API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        log.info("WhatsApp not configured — skipping send")
        return
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.post(
            f"{GRAPH_API_URL}/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text},
            },
        )
        if res.status_code not in (200, 201):
            log.warning("Send failed (%s): %s", res.status_code, res.text[:200])


async def wa_download_audio(media_id: str) -> str | None:
    """Download a WhatsApp voice note to a temp file. Returns path or None."""
    if not WHATSAPP_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=30.0) as client:
        meta = await client.get(
            f"{GRAPH_API_URL}/{media_id}",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        )
        if meta.status_code != 200:
            log.warning("Failed to get media URL: %s", meta.status_code)
            return None
        dl_url = meta.json().get("url")
        if not dl_url:
            return None

        audio = await client.get(dl_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"})
        if audio.status_code != 200:
            log.warning("Failed to download audio: %s", audio.status_code)
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            tmp.write(audio.content)
            return tmp.name


# ── User state ───────────────────────────────────────────────────────────────

async def get_or_create_user(phone: str) -> dict:
    """Get or create a WhatsApp user record in Supabase."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url(f"whatsapp_users?phone=eq.{_q(phone)}&select=*"),
            headers=service_headers(),
        )
        rows = res.json() if res.status_code == 200 else []
        if rows:
            return rows[0]

        link_code = secrets.token_urlsafe(6)[:8].upper()
        expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        new_user = {
            "phone": phone, "state": "NEW", "hourly_rate": DEFAULT_RATE,
            "link_code": link_code, "link_code_expires_at": expires,
        }
        res = await client.post(
            rest_url("whatsapp_users"),
            headers=service_headers(prefer="return=representation"),
            json=new_user,
        )
        if res.status_code in (200, 201) and res.text.strip():
            return res.json()[0]
        # 409 = concurrent insert for the same phone (unique constraint) — re-read
        res = await client.get(
            rest_url(f"whatsapp_users?phone=eq.{_q(phone)}&select=*"),
            headers=service_headers(),
        )
        rows = res.json() if res.status_code == 200 else []
        if rows:
            return rows[0]
        log.error("Failed to create WhatsApp user: %s %s", res.status_code, res.text[:200])
        return new_user


async def update_user(phone: str, updates: dict) -> None:
    """Update a WhatsApp user's state/rate/pending entry."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        await client.patch(
            rest_url(f"whatsapp_users?phone=eq.{_q(phone)}"),
            headers=service_headers(),
            json=updates,
        )


async def save_billing(wa_user: dict, entry_data: dict) -> bool:
    """Save an approved WhatsApp billing entry to billing_entries."""
    row = {
        "client_name": entry_data.get("client_name", "Unknown"),
        "matter_description": entry_data.get("matter_description", ""),
        "duration": entry_data.get("duration", "0h"),
        "billable_amount": entry_data.get("billable_amount", "R0"),
        "source": "whatsapp",
        "wa_phone": wa_user.get("phone", ""),
    }
    if wa_user.get("user_id"):
        row["user_id"] = wa_user["user_id"]

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.post(
            rest_url("billing_entries"),
            headers=service_headers(),
            json=row,
        )
        if res.status_code not in (200, 201):
            log.error("Save failed: %s %s", res.status_code, res.text[:200])
        return res.status_code in (200, 201)


# ── Voice note pipeline ──────────────────────────────────────────────────────

async def process_voice_note(phone: str, media_id: str) -> None:
    """Background task: download audio → Gemini extract → reply with summary."""
    wa_user = await get_or_create_user(phone)
    hourly_rate = wa_user.get("hourly_rate", DEFAULT_RATE)

    await wa_send(phone, "Processing your voice note...")

    tmp_path = await wa_download_audio(media_id)
    if not tmp_path:
        await wa_send(phone, "Could not download the voice note. Please try again.")
        return

    gemini = None
    uploaded = None
    try:
        gemini = genai.Client(api_key=API_KEY)
        uploaded = await asyncio.to_thread(gemini.files.upload, file=tmp_path)

        policy_context: str | None = None
        if _VECTOR_STORE:
            try:
                chunks = await asyncio.to_thread(
                    _VECTOR_STORE.retrieve, "billing rates and policy modifiers", 3
                )
                if chunks:
                    policy_context = "\n\n".join(c["text"] for c in chunks)
            except Exception as rag_err:
                log.warning("RAG retrieval failed: %s", rag_err)

        result = await asyncio.to_thread(
            extract_billing, gemini, uploaded, MODEL_NAME,
            build_prompt(hourly_rate, policy_context),
        )

        if not result.entries:
            await wa_send(phone, "Could not extract billing data from that recording.\nTry again with a clearer voice note.")
            await update_user(phone, {"state": "READY"})
            return

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
        await wa_send(phone, summary)
        await update_user(phone, {
            "state": "AWAITING_APPROVAL",
            "pending_entry": entry.model_dump(),
        })

    except Exception as e:
        log.error("Processing failed for %s: %s", phone, e)
        await wa_send(phone, "Something went wrong. Please try again.")
        await update_user(phone, {"state": "READY"})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if uploaded and gemini:
            try:
                await asyncio.to_thread(gemini.files.delete, name=uploaded.name)
            except Exception:
                pass


# ── Conversation handlers ────────────────────────────────────────────────────

WELCOME = (
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


async def handle_audio_message(phone: str, media_id: str, schedule_task) -> None:
    """Route an incoming voice note based on user state.

    schedule_task: callable(coro_fn, *args) — the router passes
    BackgroundTasks.add_task so processing happens after the 200 response.
    """
    wa_user = await get_or_create_user(phone)
    state = wa_user.get("state", "NEW")

    if state == "NEW":
        await wa_send(phone, WELCOME)
        await update_user(phone, {"state": "AWAITING_RATE"})
    elif state == "AWAITING_RATE":
        await wa_send(phone, "Set your hourly rate first.\nReply with a number, e.g. *3500*")
    else:  # READY or AWAITING_APPROVAL
        schedule_task(process_voice_note, phone, media_id)


async def handle_text_message(phone: str, text: str) -> None:
    """Route an incoming text message based on user state."""
    wa_user = await get_or_create_user(phone)
    state = wa_user.get("state", "NEW")
    upper = text.upper().strip()

    if state == "NEW":
        await wa_send(phone, WELCOME)
        await update_user(phone, {"state": "AWAITING_RATE"})

    elif state == "AWAITING_RATE":
        cleaned = text.replace("R", "").replace("r", "").replace(",", "").replace(" ", "").strip()
        if cleaned.isdigit() and int(cleaned) > 0:
            rate = int(cleaned)
            await update_user(phone, {"hourly_rate": rate, "state": "READY"})
            await wa_send(phone, (
                f"Rate set to *R{rate:,}/hr*.\n"
                f"\n"
                f"Send a voice note to get started.\n"
                f"\n"
                f"_Commands:_\n"
                f"RATE — update hourly rate\n"
                f"LINK — connect web dashboard\n"
                f"HELP — show commands"
            ))
        else:
            await wa_send(phone, "Reply with a valid number, e.g. *3500*")

    elif state == "AWAITING_APPROVAL":
        if upper == "YES":
            pending = wa_user.get("pending_entry")
            if pending:
                ok = await save_billing(wa_user, pending)
                if ok:
                    await wa_send(phone, f"Saved to your ledger.\n{APP_URL}")
                else:
                    await wa_send(phone, "Failed to save. Please try again.")
            else:
                await wa_send(phone, "No pending entry. Send a new voice note.")
            await update_user(phone, {"state": "READY", "pending_entry": None})

        elif upper == "NO":
            await wa_send(phone, "Entry discarded.")
            await update_user(phone, {"state": "READY", "pending_entry": None})

        elif upper == "EDIT":
            await wa_send(phone, f"Edit on web:\n{APP_URL}/review")
            await update_user(phone, {"state": "READY"})

        else:
            await wa_send(phone, "Reply *YES* to save, *NO* to discard, or *EDIT* to modify on web.")

    elif state == "READY":
        if upper.startswith("RATE"):
            parts = upper.replace("RATE", "").strip().replace("R", "").replace(",", "")
            if parts.isdigit() and int(parts) > 0:
                rate = int(parts)
                await update_user(phone, {"hourly_rate": rate})
                await wa_send(phone, f"Rate updated to *R{rate:,}/hr*.")
            else:
                await wa_send(phone, "Usage: *RATE 4000*")

        elif upper == "LINK":
            code = secrets.token_urlsafe(6)[:8].upper()
            expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            await update_user(phone, {"link_code": code, "link_code_expires_at": expires})
            await wa_send(phone, (
                f"Link your WhatsApp to your web account:\n"
                f"{APP_URL}/whatsapp/link/{code}\n"
                f"\n"
                f"Your link code: *{code}*"
            ))

        elif upper == "HELP":
            rate = wa_user.get("hourly_rate", DEFAULT_RATE)
            await wa_send(phone, (
                f"*LexFlow Commands*\n"
                f"\n"
                f"Voice note — extract billing entry\n"
                f"RATE [amount] — update rate (current: R{rate:,}/hr)\n"
                f"LINK — connect to web dashboard\n"
                f"HELP — show this list"
            ))

        else:
            await wa_send(phone, "Send a voice note to extract billing, or type *HELP* for commands.")
