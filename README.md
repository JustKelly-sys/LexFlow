# LexFlow

**Billing Intelligence Platform for Legal Professionals**

**[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing intelligence platform built for South African attorneys and law firms. Dictate or upload a voice note, and LexFlow transcribes it with Google Gemini, extracts structured billing entities, and presents an editable review form for human verification before committing to your personal ledger -- all scoped to your authenticated profile with Row Level Security.

---

## How It Works

1. **Sign Up** -- Create an account with your email and set your custom hourly rate (ZAR)
2. **Dictate or Upload** -- Record a voice note in-browser or upload an audio file
3. **Review & Approve** -- Extracted billing data appears in an editable form for human verification
4. **Ledger Entry** -- Approved records are saved to your personal billing ledger

> **Recruiters:** Click **"Try Demo"** on the login page -- no signup required.

---

## Features

### Core Pipeline
- **Voice Dictation** -- Record directly from the browser with real-time waveform visualization
- **Audio Upload** -- Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG
- **Gemini Extraction** -- Structured entity extraction (client name, matter, duration, amount) with Pydantic validation
- **Custom Billing Rates** -- Each user's hourly rate is dynamically applied during extraction

### Human-in-the-Loop (HITL)
- **Editable Review Form** -- Verify and correct all fields before saving
- **Confidence Scoring** -- Visual confidence bar shows extraction accuracy
- **Approve or Discard** -- Nothing saves to the database until the user explicitly approves
- **Batch Approval** -- Approve all entries at once with failure tracking and retry

### Authentication & Security
- **Supabase Auth** -- Email + password with JWT session management
- **Row Level Security** -- Users only see their own billing data
- **POPIA Compliance** -- Audio files are scrubbed from Gemini immediately after extraction
- **Input Validation** -- All billing fields validated for length and content

### Pages
- **Dashboard** -- Stat strip (real data-quality metrics), recent entries, quick navigation
- **Active Dictation** -- Bento-box layout with live waveform, Web Speech API preview, extraction sidebar
- **Review Entry** -- Editable HITL form with live entry preview and confidence bar
- **Entry Detail** -- Full billing entry view with stable reference numbers and working delete
- **Billing Ledger** -- Full history with clickable rows, CSV export, PDF invoice generation
- **Data Quality Report** -- Analyses billing data completeness (client ID rate, description quality, duration accuracy)

### Design
- **Warm Cream Aesthetic** -- Premium legal-tech palette (#FDFCF6 background, Playfair Display headings)
- **Bento Card Architecture** -- Clean white cards with soft borders
- **Tabular Numbers** -- All financial figures use tabular-nums for column alignment
- **PDF Invoice Generation** -- Branded invoices with jsPDF + autoTable
- **Mobile Responsive** -- Hamburger menu navigation for mobile devices

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Sonner, react-router-dom, jsPDF |
| **Backend** | Python, FastAPI, Uvicorn, httpx |
| **AI** | Google Gemini API (gemini-2.0-flash) |
| **Database** | Supabase (PostgreSQL + Row Level Security) |
| **Auth** | Supabase Auth (email + password, JWT) |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Architecture

```
LexFlow/
  main.py                    # FastAPI backend + Gemini + Supabase REST
  requirements.txt           # Python dependencies (pinned)
  render.yaml                # Render deployment config
  tests/
    test_lexflow.py           # 28 tests: schemas, CRUD, CORS, validation
  frontend/
    src/
      App.tsx                 # Auth shell + route wiring + ErrorBoundary
      lib/
        types.ts              # Shared interfaces (UserProfile, PendingReview, ExtractedEntry)
        supabaseClient.ts     # Supabase browser client (env vars)
        formatters.ts         # ZAR currency & duration formatting
      pages/
        DashboardPage.tsx     # Hub: real metrics, CTAs, recent entries
        DictationPage.tsx     # Recording + waveform + extraction sidebar
        ReviewPage.tsx        # HITL review form + confidence bar
        EntryDetailPage.tsx   # Full entry detail view
        LedgerPage.tsx        # Billing ledger + CSV export + invoices
        FicaPage.tsx          # Data quality report
      components/
        lexflow/
          AuthPage.tsx        # Login / signup / onboarding / demo
          Navbar.tsx          # LEX FLOW logo + nav + mobile hamburger
          BillingLedger.tsx   # Ledger table with inline delete
          MetricsStrip.tsx    # Reusable stat strip
          ErrorBoundary.tsx   # Crash recovery wrapper
          WaveformVisualizer.tsx  # Web Audio API waveform
          InvoiceGenerator.tsx    # PDF invoice (jsPDF + autoTable)
```

**Routes:**

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Real metrics, recent entries, New Dictation + Upload CTAs |
| `/dictate` | Dictation | Live recording with waveform + extraction sidebar |
| `/review` | Review | Editable HITL form with confidence bar |
| `/entry/:id` | Entry Detail | Full detail with delete functionality |
| `/ledger` | Ledger | Billing table with CSV export + PDF invoice generation |
| `/fica` | Data Quality | Analyses billing data completeness and accuracy |

**Data Flow:** Browser -> FastAPI -> Gemini (extract) -> User Review (HITL) -> Supabase (save) -> Dashboard

---

## Getting Started

```bash
git clone https://github.com/JustKelly-sys/LexFlow.git
cd LexFlow

# Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..

# Environment (.env)
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Run
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## API Endpoints

All endpoints except the frontend require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | React SPA (dashboard) |
| POST | `/transcribe` | Extract billing data from audio |
| POST | `/billing` | Save a user-approved billing entry |
| GET | `/billing` | Get authenticated user's billing entries |
| GET | `/billing/csv` | Download billing data as CSV |
| DELETE | `/billing/{id}` | Delete a billing entry (verified) |
| GET | `/profile` | Get user profile |
| PATCH | `/profile` | Update profile (name, firm, rate) |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI over Django** | Async-first -- handles Gemini API latency without blocking |
| **Supabase over Firebase** | Postgres + Row Level Security + built-in auth REST API |
| **httpx over supabase-py** | Avoids C-extension build failures on Windows/Render |
| **HITL over auto-save** | Legal billing demands accuracy -- AI extraction is a draft, not a fact |
| **Bento layout** | Premium legal aesthetic; cleaner and more professional |
| **Playfair Display serif** | Conveys authority and trust appropriate for legal tech |

---

## Testing

```bash
# Run all 28 tests
python -m pytest tests/test_lexflow.py -v
```

Covers: Pydantic schemas, prompt builder, file validation, billing CRUD, CSV export, CORS config, DELETE endpoint, input validation.

---

## License

MIT

## Author

**Tshepiso Jafta** -- [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
