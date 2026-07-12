"""
Vercel serverless entrypoint — exposes the FastAPI app as an ASGI function.

Vercel serves frontend/dist statically and rewrites API paths here (see
vercel.json). The heavy RAG/LangGraph dependencies are excluded from
api/requirements.txt, so those layers degrade gracefully to the direct
Gemini extraction path.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app  # noqa: E402,F401  (ASGI app picked up by Vercel)
