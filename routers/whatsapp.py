"""
WhatsApp webhook endpoints — Meta verification, message intake, account linking.
"""
import hmac
import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote as _q

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from auth import get_current_user
from config import HTTP_TIMEOUT, WEBHOOK_VERIFY_TOKEN
from services.supabase import rest_url, service_headers
from services.whatsapp import (
    handle_audio_message,
    handle_text_message,
    verify_webhook_signature,
)

log = logging.getLogger("lexflow.webhook")

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta sends this GET to verify the webhook URL during setup."""
    if mode == "subscribe" and hmac.compare_digest(token or "", WEBHOOK_VERIFY_TOKEN):
        log.info("Webhook verified")
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(403, "Webhook verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, bg: BackgroundTasks):
    """Receive incoming WhatsApp messages. Must return 200 immediately."""
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(raw_body, sig):
        log.warning("Webhook signature verification failed")
        raise HTTPException(401, "Invalid signature")
    body = json.loads(raw_body)

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
            await handle_audio_message(phone, msg["audio"]["id"], bg.add_task)
        elif msg_type == "text":
            await handle_text_message(phone, msg.get("text", {}).get("body", "").strip())

    return {"status": "ok"}


@router.post("/whatsapp/link")
async def link_whatsapp(request: Request, user: dict = Depends(get_current_user)):
    """Link a WhatsApp number to a web account using a link code."""
    body = await request.json()
    code = body.get("code", "").strip().upper()
    if not code:
        raise HTTPException(400, "Missing link code")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url(f"whatsapp_users?link_code=eq.{_q(code)}&select=*"),
            headers=service_headers(),
        )
        rows = res.json() if res.status_code == 200 else []
        if not rows:
            raise HTTPException(404, "Invalid link code")

        wa_user = rows[0]
        expires_at = wa_user.get("link_code_expires_at")
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp_dt:
                    raise HTTPException(410, "Link code has expired. Type LINK in WhatsApp to get a new one.")
            except (ValueError, TypeError):
                pass  # If parsing fails, allow linking (backward compat)
        if wa_user.get("user_id") and wa_user["user_id"] != user["id"]:
            raise HTTPException(409, "This WhatsApp number is already linked to another account")

        await client.patch(
            rest_url(f"whatsapp_users?link_code=eq.{_q(code)}"),
            headers=service_headers(),
            json={"user_id": user["id"]},
        )

        # Retroactively claim any unlinked WhatsApp billing entries from this phone
        phone = wa_user["phone"]
        unlinked = await client.get(
            rest_url(f"billing_entries?user_id=is.null&source=eq.whatsapp&wa_phone=eq.{_q(phone)}&select=id"),
            headers=service_headers(),
        )
        if unlinked.status_code == 200 and unlinked.json():
            for entry in unlinked.json():
                await client.patch(
                    rest_url(f"billing_entries?id=eq.{_q(str(entry['id']))}"),
                    headers=service_headers(),
                    json={"user_id": user["id"]},
                )

    return JSONResponse(content={"status": "linked", "phone": wa_user["phone"]})
