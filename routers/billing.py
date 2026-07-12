"""
Billing endpoints — transcription, CRUD, CSV export, demo seeding.
"""
import asyncio
import csv
import io
import logging
import os
import tempfile
from urllib.parse import quote as _q

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from google import genai

from auth import get_current_user
from config import (
    ALLOWED_AUDIO_EXTS,
    API_KEY,
    CONFIDENCE_THRESHOLD,
    DEMO_EMAIL,
    HTTP_TIMEOUT,
    MAX_AUDIO_BYTES,
    MODEL_NAME,
)
from services.gemini import TranscriptionResult, BillingEntry, build_prompt, extract_billing, get_hourly_rate
from services.supabase import headers, rest_url, service_headers

log = logging.getLogger("lexflow.billing")

router = APIRouter()

# RAG layer — optional; the app runs fine without it
try:
    from services.vector_store import VectorStore
    _VECTOR_STORE: "VectorStore | None" = VectorStore()
    log.info("LanceDB loaded: %d policy chunks", _VECTOR_STORE.count())
except Exception as e:
    _VECTOR_STORE = None
    log.info("Vector store unavailable (%s) — running without policy context", e)

# LangGraph billing pipeline — optional; falls back to direct Gemini call
try:
    from services.billing_graph import run_billing_graph
    _GRAPH_AVAILABLE = True
    log.info("LangGraph billing pipeline loaded")
except Exception as e:
    run_billing_graph = None
    _GRAPH_AVAILABLE = False
    log.info("LangGraph unavailable (%s) — falling back to direct Gemini call", e)


async def _save_upload_capped(file: UploadFile, suffix: str) -> str:
    """Stream the upload to a temp file, enforcing MAX_AUDIO_BYTES even when
    the client omits Content-Length. Returns the temp path."""
    written = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_AUDIO_BYTES:
                tmp.close()
                os.remove(tmp_path)
                raise HTTPException(413, "File too large. Maximum size is 25 MB.")
            tmp.write(chunk)
    return tmp_path


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload audio → Gemini extracts billing fields → return for HITL review."""
    if not API_KEY:
        raise HTTPException(500, "Server misconfigured: missing GOOGLE_API_KEY")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'")

    hourly_rate = await get_hourly_rate(user)
    gemini = genai.Client(api_key=API_KEY)
    tmp_path = None
    uploaded = None

    try:
        tmp_path = await _save_upload_capped(file, ext)
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

        audit_log: list[str] = []
        if _GRAPH_AVAILABLE:
            graph_result = await asyncio.to_thread(
                run_billing_graph, uploaded, hourly_rate, "", policy_context,
            )
            result = TranscriptionResult(
                entries=[BillingEntry(**e) for e in graph_result["entries"]],
                confidence=graph_result["confidence"],
            )
            needs_review = graph_result["needs_human_review"]
            audit_log = graph_result["audit_log"]
            for line in audit_log:
                log.info("[graph] %s", line)
        else:
            result = await asyncio.to_thread(
                extract_billing, gemini, uploaded, MODEL_NAME,
                build_prompt(hourly_rate, policy_context),
            )
            needs_review = result.confidence < CONFIDENCE_THRESHOLD

        log.info(
            "transcribed: rate=%s entries=%d confidence=%.2f needs_review=%s",
            hourly_rate, len(result.entries), result.confidence, needs_review,
        )
        return JSONResponse(content={
            **result.model_dump(),
            "needs_human_review": needs_review,
            "audit_log": audit_log,
        })

    except HTTPException:
        raise
    except Exception as e:
        log.error("Transcription failed: %s", e)
        raise HTTPException(500, "Audio processing failed. Please try again or contact support.")
    finally:
        # POPIA: scrub temp file + Gemini upload immediately
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if uploaded:
            try:
                await asyncio.to_thread(gemini.files.delete, name=uploaded.name)
                log.info("[POPIA] Deleted Gemini upload: %s", uploaded.name)
            except Exception:
                pass


# ── Billing CRUD ─────────────────────────────────────────────────────────────

@router.post("/billing")
async def save_billing_entry(request: Request, user: dict = Depends(get_current_user)):
    """Save a user-approved billing entry (HITL approve action)."""
    body = await request.json()
    required = {"client_name", "matter_description", "duration", "billable_amount"}
    missing = required - set(body.keys())
    if missing:
        raise HTTPException(400, f"Missing fields: {missing}")

    for field in required:
        val = str(body[field])
        if len(val) > 2000:
            raise HTTPException(400, f"Field '{field}' exceeds maximum length (2000 chars)")
        if len(val.strip()) == 0:
            raise HTTPException(400, f"Field '{field}' cannot be empty")

    row = {"user_id": user["id"], **{k: body[k] for k in required}}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.post(
            rest_url("billing_entries"),
            headers=headers(user["token"]),
            json=row,
        )
    if res.status_code not in (200, 201):
        raise HTTPException(500, f"Failed to save: {res.text}")
    return JSONResponse(content={"status": "saved"}, status_code=201)


@router.get("/billing")
async def get_billing(user: dict = Depends(get_current_user)):
    """Return all billing entries for the authenticated user (RLS-enforced)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url("billing_entries?select=*&order=created_at.desc"),
            headers=headers(user["token"]),
        )
    if res.status_code != 200:
        return JSONResponse(content={"count": 0, "entries": []})
    entries = res.json()
    return JSONResponse(content={"count": len(entries), "entries": entries})


@router.get("/billing/csv")
async def download_csv(user: dict = Depends(get_current_user)):
    """Export billing entries as a downloadable CSV file."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url("billing_entries?select=*&order=created_at.desc"),
            headers=headers(user["token"]),
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


@router.delete("/billing/{entry_id}")
async def delete_billing_entry(entry_id: str, user: dict = Depends(get_current_user)):
    """Delete a specific billing entry by ID (must belong to authenticated user)."""
    hdrs = headers(user["token"])
    hdrs["Prefer"] = "return=representation"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.delete(
            rest_url(f"billing_entries?id=eq.{_q(entry_id)}&user_id=eq.{_q(user['id'])}"),
            headers=hdrs,
        )
    if res.status_code not in (200, 204):
        raise HTTPException(500, "Failed to delete entry")
    deleted_rows = res.json() if res.text.strip() else []
    if not deleted_rows:
        raise HTTPException(404, "Entry not found or access denied")
    return JSONResponse(content={"status": "deleted"})


@router.patch("/billing/{entry_id}")
async def update_billing_entry(entry_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Update a billing entry's fields (must belong to authenticated user)."""
    body = await request.json()
    allowed = {"client_name", "matter_description", "duration", "billable_amount"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(400, "No valid fields to update")
    for field, val in update.items():
        if len(str(val)) > 2000:
            raise HTTPException(400, f"Field '{field}' exceeds maximum length")
        if len(str(val).strip()) == 0:
            raise HTTPException(400, f"Field '{field}' cannot be empty")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        check = await client.get(
            rest_url(f"billing_entries?id=eq.{_q(entry_id)}&user_id=eq.{_q(user['id'])}&select=id"),
            headers=headers(user["token"]),
        )
        if check.status_code != 200 or not check.json():
            raise HTTPException(404, "Entry not found or access denied")
        res = await client.patch(
            rest_url(f"billing_entries?id=eq.{_q(entry_id)}&user_id=eq.{_q(user['id'])}"),
            headers=headers(user["token"]),
            json=update,
        )
    if res.status_code not in (200, 204):
        raise HTTPException(500, f"Failed to update: {res.text}")
    return JSONResponse(content={"status": "updated"})


# ── Demo seeder ──────────────────────────────────────────────────────────────

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


@router.post("/demo/seed")
async def seed_demo_data(user: dict = Depends(get_current_user)):
    """Wipe and re-seed the demo account with fresh sample billing data."""
    # get_current_user already verified the JWT — the email is trustworthy
    if user.get("email", "") != DEMO_EMAIL:
        raise HTTPException(403, "Demo seed is only for demo accounts")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        del_res = await client.delete(
            rest_url(f"billing_entries?user_id=eq.{user['id']}"),
            headers=service_headers(),
        )
        log.info("Demo wipe: %s", del_res.status_code)
        for entry in DEMO_ENTRIES:
            await client.post(
                rest_url("billing_entries"),
                headers=headers(user["token"]),
                json={"user_id": user["id"], **entry},
            )
    return JSONResponse(content={"status": "demo_seeded", "entries": len(DEMO_ENTRIES)})
