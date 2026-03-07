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

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in .env file.")

# --- Pydantic schema for structured Gemini output ---
class BillingEntry(BaseModel):
    client_name: str
    matter_description: str
    duration: str
    billable_amount: str

# --- App setup ---
app = FastAPI(title="LexFlow API", version="2.0")

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


# --- Dashboard HTML ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LexFlow | Billing Intelligence</title>
    <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Source Sans 3', 'Segoe UI', sans-serif;
            background: #f5f4f0;
            color: #1a1a1a;
            min-height: 100vh;
        }
        .header {
            background: #0c1a2e;
            padding: 0;
            border-bottom: 3px solid #8b1a2b;
        }
        .header-inner {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1.6rem 2.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.6rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
        }
        .header h1 span { color: #c4975c; }
        .header-subtitle {
            color: #7a8a9e;
            font-size: 0.8rem;
            font-weight: 400;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-top: 0.2rem;
        }
        .header-right {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        .live-badge {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7a8a9e;
        }
        .live-dot {
            width: 7px; height: 7px;
            border-radius: 50%;
            background: #2d8a4e;
            animation: pulse 2.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 2.5rem 3rem;
        }
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1px;
            background: #d4cfc5;
            border: 1px solid #d4cfc5;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: #ffffff;
            padding: 1.4rem 1.6rem;
        }
        .stat-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #6b7280;
            margin-bottom: 0.4rem;
            font-weight: 600;
        }
        .stat-value {
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: #0c1a2e;
        }
        .controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e5e1d8;
        }
        .controls-title {
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: #0c1a2e;
        }
        .controls-right { display: flex; gap: 0.6rem; }
        .btn {
            font-family: 'Source Sans 3', sans-serif;
            background: #0c1a2e;
            border: none;
            color: #ffffff;
            padding: 0.5rem 1.2rem;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            transition: background 0.15s;
        }
        .btn:hover { background: #142d4a; }
        .btn-outline {
            background: transparent;
            border: 1px solid #c4bfb3;
            color: #4a4a4a;
        }
        .btn-outline:hover { background: #eae6de; border-color: #a09a8e; }
        .table-wrapper {
            background: #ffffff;
            border: 1px solid #d4cfc5;
            border-radius: 4px;
            overflow: hidden;
        }
        table { width: 100%; border-collapse: collapse; }
        thead th {
            background: #f7f5f1;
            padding: 0.8rem 1.2rem;
            text-align: left;
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #6b7280;
            font-weight: 700;
            border-bottom: 2px solid #d4cfc5;
        }
        tbody td {
            padding: 0.85rem 1.2rem;
            font-size: 0.88rem;
            border-bottom: 1px solid #edebe6;
            color: #333;
        }
        tbody tr:hover td { background: #faf9f6; }
        tbody tr:last-child td { border-bottom: none; }
        .col-timestamp { color: #7a7a7a; font-size: 0.78rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
        .col-client { color: #0c1a2e; font-weight: 600; }
        .col-matter { color: #4a4a4a; max-width: 340px; }
        .col-duration { color: #0c1a2e; font-weight: 500; text-align: center; }
        .col-amount {
            font-family: 'Libre Baskerville', Georgia, serif;
            color: #2d6b3f;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            text-align: right;
        }
        .empty-state { text-align: center; padding: 4rem 2rem; color: #8a8a8a; }
        .empty-state .icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
        .empty-state p { font-size: 0.9rem; line-height: 1.6; }
        .empty-state code { background: #f0ede6; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.82rem; color: #8b1a2b; }
        .footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
            padding-top: 0.8rem;
            font-size: 0.72rem;
            color: #9a9a9a;
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .new-row td { animation: fadeIn 0.5s ease-out; }
        @media (max-width: 768px) {
            .stats-bar { grid-template-columns: 1fr; }
            .header-inner { flex-direction: column; align-items: flex-start; gap: 0.8rem; }
            .controls { flex-direction: column; align-items: flex-start; gap: 0.8rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <div>
                <h1>Lex<span>Flow</span></h1>
                <div class="header-subtitle">Billing Intelligence Platform</div>
            </div>
            <div class="header-right">
                <div class="live-badge">
                    <span class="live-dot" id="liveDot"></span>
                    Live
                </div>
            </div>
        </div>
    </div>
    <div class="content">
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-label">Total Entries</div>
                <div class="stat-value" id="totalEntries">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Billed</div>
                <div class="stat-value" id="totalAmount">R0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average per Entry</div>
                <div class="stat-value" id="avgAmount">R0</div>
            </div>
        </div>
        <div class="controls">
            <div class="controls-title">Billing Ledger</div>
            <div class="controls-right">
                <button class="btn btn-outline" onclick="downloadCSV()">Export CSV</button>
                <button class="btn" onclick="fetchBilling()">Refresh</button>
            </div>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th style="width:150px">Date</th>
                        <th>Client</th>
                        <th>Matter</th>
                        <th style="text-align:center">Duration</th>
                        <th style="text-align:right">Amount (ZAR)</th>
                    </tr>
                </thead>
                <tbody id="billingBody"></tbody>
            </table>
        </div>
        <div class="footer">
            <span id="lastUpdated"></span>
            <span>LexFlow v2.0</span>
        </div>
    </div>
    <script>
        let lastCount = -1;
        let refreshInterval;
        function formatTimestamp(iso) {
            const d = new Date(iso);
            return d.toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })
                + '  ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
        }
        function parseAmount(str) {
            const match = str.replace(/\\s/g, '').match(/R?([\\d,.]+)/i);
            return match ? parseFloat(match[1].replace(/,/g, '')) : 0;
        }
        function formatCurrency(num) {
            return 'R' + num.toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        }
        async function fetchBilling() {
            try {
                const res = await fetch('/billing');
                const data = await res.json();
                const entries = data.entries;
                const isNew = entries.length !== lastCount;
                lastCount = entries.length;
                document.getElementById('totalEntries').textContent = entries.length;
                let total = 0;
                entries.forEach(e => total += parseAmount(e['Billable Amount'] || '0'));
                document.getElementById('totalAmount').textContent = formatCurrency(total);
                document.getElementById('avgAmount').textContent =
                    entries.length > 0 ? formatCurrency(Math.round(total / entries.length)) : 'R0';
                const tbody = document.getElementById('billingBody');
                if (entries.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="icon">&#9878;</div><p>No billing entries recorded.<br>Submit a voice note via <code>POST /transcribe</code> to begin.</p></div></td></tr>';
                } else {
                    const reversed = [...entries].reverse();
                    tbody.innerHTML = reversed.map((e, i) =>
                        '<tr class="' + (isNew && i === 0 ? 'new-row' : '') + '">' +
                        '<td class="col-timestamp">' + formatTimestamp(e['Timestamp']) + '</td>' +
                        '<td class="col-client">' + e['Client Name'] + '</td>' +
                        '<td class="col-matter">' + e['Matter Description'] + '</td>' +
                        '<td class="col-duration">' + e['Duration'] + '</td>' +
                        '<td class="col-amount">' + e['Billable Amount'] + '</td>' +
                        '</tr>'
                    ).join('');
                }
                document.getElementById('lastUpdated').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
            } catch (err) {
                console.error('Fetch error:', err);
            }
        }
        function downloadCSV() { window.open('/billing/csv', '_blank'); }
        fetchBilling();
        refreshInterval = setInterval(fetchBilling, 10000);
    </script>
</body>
</html>
"""


# --- Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the live billing dashboard."""
    return DASHBOARD_HTML


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
            "- billable_amount: Calculate at R2500/hr (e.g. if 2 hours → 'R5000')\n\n"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
