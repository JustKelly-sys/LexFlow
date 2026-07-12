"""
LexFlow — Billing Intelligence Platform

Converts voice dictations into structured billing entries for legal professionals
using Google Gemini AI. Supabase handles auth (JWT) and data (Postgres + RLS).

App assembly only — endpoints live in routers/, integrations in services/.

Author: Tshepiso Jafta
Version: 5.0 — modular refactor
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import ALLOWED_AUDIO_EXTS, APP_URL, FRONTEND_DIST  # noqa: F401 (test re-export)
from auth import get_current_user  # noqa: F401 (test re-export)
from services.gemini import BillingEntry, TranscriptionResult, build_prompt  # noqa: F401
from routers import billing, profile, whatsapp

log = logging.getLogger("lexflow")

# Backward-compatible aliases (tests and older callers import these from main)
_build_prompt = build_prompt

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Build the policy index on first boot (empty index) without blocking startup.

    Failures are logged, never fatal — the app degrades gracefully to no-RAG mode.
    """
    store = billing._VECTOR_STORE
    if store is not None:
        def _ingest_if_empty():
            try:
                if store.count() == 0:
                    from scripts.ingest_policies import ingest_all
                    n = ingest_all(store)
                    log.info("Policy index built: %d chunks", n)
            except Exception as e:
                log.warning("Policy ingestion failed (%s) — continuing without RAG", e)

        asyncio.get_running_loop().run_in_executor(None, _ingest_if_empty)
    yield


app = FastAPI(title="LexFlow API", version="5.0", lifespan=lifespan)

_cors_origins = ["http://localhost:8000", "http://localhost:5173"]
if APP_URL not in _cors_origins:
    _cors_origins.append(APP_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(billing.router)
app.include_router(profile.router)
app.include_router(whatsapp.router)


@app.get("/health")
async def health():
    """Liveness probe for the hosting platform."""
    return {"status": "ok", "version": app.version}


# ── Static frontend serving — catch-all, registered LAST ────────────────────

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
