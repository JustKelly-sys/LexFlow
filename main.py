"""
LexFlow - Billing Intelligence Platform

A FastAPI application that converts attorney voice notes into structured
billing entries using Google Gemini AI. Uses Supabase for auth and data storage.

Author: Tshepiso Jafta
Version: 3.0
"""
import os
import json
import shutil
import tempfile
import time
import httpx
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv
import io
import csv

# Load environment variables
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in .env file.")
if not SUPABASE_URL:
    print("WARNING: SUPABASE_URL not found in .env file.")

# --- Supabase REST helpers ---
def supabase_headers(user_token: str = None):
    """Headers for Supabase REST API calls."""
    key = user_token or SUPABASE_SERVICE_KEY
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def supabase_rest(path: str):
    """Build full Supabase REST URL."""
    return f"{SUPABASE_URL}/rest/v1/{path}"

def supabase_auth(path: str):
    """Build full Supabase Auth URL."""
    return f"{SUPABASE_URL}/auth/v1/{path}"

# --- Auth dependency ---
async def get_current_user(request: Request) -> dict:
    """Extract and verify user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            supabase_auth("user"),
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {token}"}
        )
        if res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return {**res.json(), "token": token}

# --- Pydantic schema ---
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

# --- Gemini call with retry ---
def call_gemini_with_retry(client: genai.Client, uploaded_file, model: str, prompt: str) -> BillingEntry:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[uploaded_file, prompt],
                config={"response_mime_type": "application/json", "response_schema": BillingEntry},
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
# API ENDPOINTS
# =====================================================

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: missing GOOGLE_API_KEY")
    
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'")

    # Get user's hourly rate from profile
    async with httpx.AsyncClient(timeout=15.0) as client_http:
        profile_res = await client_http.get(
            supabase_rest(f"profiles?id=eq.{user['id']}&select=hourly_rate"),
            headers=supabase_headers(user["token"])
        )
        print(f"[RATE LOOKUP] status={profile_res.status_code}, data={profile_res.text}")
        hourly_rate = 2500
        if profile_res.status_code == 200:
            profiles = profile_res.json()
            if profiles:
                hourly_rate = profiles[0].get("hourly_rate", 2500)

    gemini_client = genai.Client(api_key=API_KEY)
    tmp_path = None
    uploaded_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        uploaded_file = gemini_client.files.upload(file=tmp_path)

        prompt = (
            f"You are a legal billing assistant. Listen to this voice note from a lawyer describing work they did for a client.\n\n"
            f"Extract these fields:\n"
            f"- client_name: The name of the client or party mentioned. If no name, use 'Unspecified Client'.\n"
            f"- matter_description: A concise summary of the legal work described.\n"
            f"- duration: The duration of the LEGAL WORK described (NOT the length of the recording). "
            f"Look for time references like 'spent 2 hours', 'took 45 minutes', 'half an hour'. "
            f"If no explicit duration is mentioned, estimate based on the complexity of work described "
            f"(brief phone call = '15 minutes', consultation = '1 hour', detailed review = '2 hours'). "
            f"Format as e.g. '2 hours' or '45 minutes'.\n"
            f"- billable_amount: You MUST calculate this. The attorney's rate is R{hourly_rate} per hour. "
            f"Multiply the duration by R{hourly_rate}/hr and format as 'RXXXX'. "
            f"Example: 2 hours at R{hourly_rate}/hr = 'R{hourly_rate * 2}'. "
            f"30 minutes at R{hourly_rate}/hr = 'R{hourly_rate // 2}'.\n\n"
            f"Return valid JSON matching the schema. Every field must have a non-empty value."
        )

        entry = call_gemini_with_retry(gemini_client, uploaded_file, MODEL_NAME, prompt)
        entry_data = entry.model_dump()
        print(f"[GEMINI RESULT] hourly_rate={hourly_rate}, raw={entry_data}")

        # HITL: Return extraction for user review — do NOT auto-save
        return JSONResponse(content=entry_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # POPIA/GDPR Compliance: scrub temp files and Gemini uploads immediately
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        try:
            if uploaded_file:
                gemini_client.files.delete(name=uploaded_file.name)
                print(f"[POPIA] Deleted Gemini upload: {uploaded_file.name}")
        except Exception:
            pass  # Best-effort cleanup


@app.post("/billing")
async def save_billing_entry(request: Request, user: dict = Depends(get_current_user)):
    """Save a user-approved billing entry (Human-in-the-Loop)."""
    body = await request.json()
    required = {"client_name", "matter_description", "duration", "billable_amount"}
    if not required.issubset(body.keys()):
        raise HTTPException(status_code=400, detail=f"Missing fields: {required - set(body.keys())}")

    async with httpx.AsyncClient(timeout=15.0) as client_http:
        insert_res = await client_http.post(
            supabase_rest("billing_entries"),
            headers=supabase_headers(user["token"]),
            json={
                "user_id": user["id"],
                "client_name": body["client_name"],
                "matter_description": body["matter_description"],
                "duration": body["duration"],
                "billable_amount": body["billable_amount"],
            }
        )
        if insert_res.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Failed to save: {insert_res.text}")
        return JSONResponse(content={"status": "saved"})



DEMO_EMAIL = "demo@lexflow.app"

DEMO_ENTRIES = [
    {
        "client_name": "Ndlovu Holdings (Pty) Ltd",
        "matter_description": "Reviewed and advised on commercial lease agreement for new Sandton office premises. Identified non-standard escalation clauses and recommended amendments.",
        "duration": "2 hours",
        "billable_amount": "R5000",
    },
    {
        "client_name": "John Mokoena",
        "matter_description": "Consultation regarding unfair dismissal claim under the LRA. Drafted referral to CCMA and prepared initial statement of case.",
        "duration": "1.5 hours",
        "billable_amount": "R3750",
    },
    {
        "client_name": "Vukani Construction",
        "matter_description": "Reviewed BBBEE compliance documentation and shareholding structure. Provided written opinion on fronting risk under the Codes of Good Practice.",
        "duration": "3 hours",
        "billable_amount": "R7500",
    },
    {
        "client_name": "Sarah van der Merwe",
        "matter_description": "Drafted antenuptial contract with accrual system. Discussed implications of matrimonial property regime and estate planning considerations.",
        "duration": "1 hour",
        "billable_amount": "R2500",
    },
    {
        "client_name": "TechBridge Solutions",
        "matter_description": "Negotiated and finalized SLA terms for cloud infrastructure agreement. Reviewed data protection clauses for POPIA compliance.",
        "duration": "2.5 hours",
        "billable_amount": "R6250",
    },
]


@app.post("/demo/seed")
async def seed_demo_data(user: dict = Depends(get_current_user)):
    """Reset and seed demo account with sample billing data."""
    # Verify this is the demo user
    async with httpx.AsyncClient(timeout=15.0) as client_http:
        # Get user email from Supabase auth
        auth_res = await client_http.get(
            supabase_auth("user"),
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {user['token']}"}
        )
        if auth_res.status_code != 200:
            raise HTTPException(status_code=403, detail="Could not verify user")
        
        user_email = auth_res.json().get("email", "")
        if user_email != DEMO_EMAIL:
            raise HTTPException(status_code=403, detail="Demo seed is only available for demo accounts")

        # Delete existing billing entries for demo user (use service key to bypass RLS)
        del_headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        del_res = await client_http.delete(
            supabase_rest(f"billing_entries?user_id=eq.{user['id']}"),
            headers=del_headers,
        )
        print(f"[DEMO SEED] Deleted old entries: {del_res.status_code}")
        
        # Insert fresh demo data
        for entry in DEMO_ENTRIES:
            await client_http.post(
                supabase_rest("billing_entries"),
                headers=supabase_headers(user["token"]),
                json={
                    "user_id": user["id"],
                    **entry,
                }
            )

        return JSONResponse(content={"status": "demo_seeded", "entries": len(DEMO_ENTRIES)})


@app.get("/billing")
async def get_billing(user: dict = Depends(get_current_user)):
    """Return billing entries for the authenticated user."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            supabase_rest("billing_entries?select=*&order=created_at.desc"),
            headers=supabase_headers(user["token"])
        )
        if res.status_code != 200:
            return JSONResponse(content={"count": 0, "entries": []})
        entries = res.json()
        return JSONResponse(content={"count": len(entries), "entries": entries})


@app.get("/billing/csv")
async def download_csv(user: dict = Depends(get_current_user)):
    """Generate CSV from Supabase billing entries."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            supabase_rest("billing_entries?select=*&order=created_at.desc"),
            headers=supabase_headers(user["token"])
        )
        entries = res.json() if res.status_code == 200 else []

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Timestamp", "Client Name", "Matter Description", "Duration", "Billable Amount"])
    writer.writeheader()
    for e in entries:
        writer.writerow({
            "Timestamp": e.get("created_at", ""),
            "Client Name": e.get("client_name", ""),
            "Matter Description": e.get("matter_description", ""),
            "Duration": e.get("duration", ""),
            "Billable Amount": e.get("billable_amount", ""),
        })
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=billing.csv"}
    )


@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            supabase_rest(f"profiles?id=eq.{user['id']}&select=*"),
            headers=supabase_headers(user["token"])
        )
        if res.status_code == 200 and res.json():
            return JSONResponse(content=res.json()[0])
        raise HTTPException(status_code=404, detail="Profile not found")


@app.patch("/profile")
async def update_profile(request: Request, user: dict = Depends(get_current_user)):
    """Update the authenticated user's profile (onboarding, rate changes, etc.)."""
    body = await request.json()
    allowed_fields = {"full_name", "firm_name", "phone", "hourly_rate", "onboarded"}
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    async with httpx.AsyncClient() as client:
        res = await client.patch(
            supabase_rest(f"profiles?id=eq.{user['id']}"),
            headers=supabase_headers(user["token"]),
            json=update_data
        )
        if res.status_code in (200, 204):
            if res.text:
                return JSONResponse(content=res.json()[0] if res.json() else {})
            return JSONResponse(content={"status": "updated"})
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {res.text}")


# =====================================================
# STATIC FRONTEND SERVING (catch-all, registered LAST)
# =====================================================
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_frontend(full_path: str):
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        return "Frontend build not found."
else:
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return "LexFlow API is running. React frontend build (frontend/dist) was not found."


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
