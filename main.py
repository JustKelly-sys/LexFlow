"""
LexFlow - Billing Intelligence Platform

A FastAPI application that converts attorney voice notes into structured
billing entries using Google Gemini AI. Designed for South African law firms
with ZAR billing rates and FICA-compliant record keeping.

Author: Tshepiso Jafta
Version: 3.0
"""
import os
import csv
import json
import shutil
import tempfile
import time
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
BILLING_FILE = "billing.csv"
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5  # seconds
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in .env file.")

# --- Pydantic schema for structured Gemini output ---
class BillingEntry(BaseModel):
    client_name: str
    matter_description: str
    duration: str
    billable_amount: str

# --- App setup ---
app = FastAPI(title="LexFlow API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CSV helpers ---
CSV_FIELDS = ["Timestamp", "Client Name", "Matter Description", "Duration", "Billable Amount"]

def save_to_csv(data: dict):
    """Append a billing record to the CSV file. Raises on failure."""
    file_exists = os.path.isfile(BILLING_FILE)
    record = {
        "Timestamp": datetime.now().isoformat(),
        "Client Name": data.get("client_name", ""),
        "Matter Description": data.get("matter_description", ""),
        "Duration": data.get("duration", ""),
        "Billable Amount": data.get("billable_amount", ""),
    }
    with open(BILLING_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

def read_csv() -> list[dict]:
    """Read billing.csv and return as a list of dicts."""
    if not os.path.isfile(BILLING_FILE):
        return []
    with open(BILLING_FILE, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

# --- Gemini call with retry ---
def call_gemini_with_retry(client: genai.Client, uploaded_file, model: str, prompt: str) -> BillingEntry:
    """Call Gemini with exponential backoff on 429 errors."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[uploaded_file, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BillingEntry,
                },
            )
            if response.parsed:
                return response.parsed
            data = json.loads(response.text)
            return BillingEntry(**data)
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise HTTPException(status_code=429, detail=f"Gemini API rate limit exceeded after {MAX_RETRIES} retries: {last_error}")


# =====================================================
# API ENDPOINTS (registered FIRST so they take priority)
# =====================================================

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # Validate API key
    if not API_KEY or API_KEY == "replace_me_with_your_actual_api_key":
        raise HTTPException(status_code=500, detail="Server misconfigured: missing GOOGLE_API_KEY in .env")

    # Validate file type
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
        )

    # Initialize Gemini client
    client = genai.Client(api_key=API_KEY)

    tmp_path = None
    try:
        # Save upload to temp file (preserving extension for Gemini)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Upload to Gemini File API
        uploaded_file = client.files.upload(file=tmp_path)

        # Prompt
        prompt = (
            "Listen to this voice note from a lawyer. Extract the following billing details:\n"
            "- client_name: The name of the client mentioned\n"
            "- matter_description: What legal work was described\n"
            "- duration: How long the work took (e.g. '2 hours', '30 minutes')\n"
            "- billable_amount: Calculate at R2500/hr (e.g. if 2 hours -> 'R5000')\n\n"
            "Return valid JSON matching the schema."
        )

        # Call Gemini with retry
        entry = call_gemini_with_retry(client, uploaded_file, MODEL_NAME, prompt)

        # Save to CSV
        save_to_csv(entry.model_dump())

        return JSONResponse(content=entry.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/billing")
async def get_billing():
    """Return all billing entries from CSV as JSON."""
    entries = read_csv()
    return JSONResponse(content={"count": len(entries), "entries": entries})


@app.get("/billing/csv")
async def download_csv():
    """Download billing.csv directly."""
    from fastapi.responses import FileResponse
    if not os.path.isfile(BILLING_FILE):
        raise HTTPException(status_code=404, detail="No billing data yet.")
    return FileResponse(BILLING_FILE, filename="billing.csv", media_type="text/csv")


# =====================================================
# STATIC FRONTEND SERVING (registered LAST = catch-all)
# =====================================================

if os.path.isdir(FRONTEND_DIST):
    # Mount compiled JS/CSS assets
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_frontend(full_path: str):
        """Serve index.html for all non-API routes (React SPA routing)."""
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        return "Frontend build not found. Run 'npm run build' in the frontend directory."
else:
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return "LexFlow API is running. React frontend build (frontend/dist) was not found."


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
