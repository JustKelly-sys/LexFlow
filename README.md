# LexFlow

**Billing Intelligence Platform for Legal Professionals**

**[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing intelligence platform built for South African attorneys and law firms. Dictate or upload a voice note, and LexFlow transcribes it with Gemini, extracts structured billing entities, and presents an editable review form for human verification before committing to your personal ledger -- all scoped to your authenticated profile with Row Level Security.

---

## How It Works

1. **Sign Up** -- Create an account with your email and set your custom hourly rate (ZAR)
2. **Dictate or Upload** -- Record a voice note in-browser or upload an audio file
3. **Review & Approve** -- Extracted billing data appears in an editable form for human verification
4. **Ledger Entry** -- Approved records are saved to your personal billing ledger with full FICA compliance

> **Recruiters:** Click **"Try Demo"** on the login page -- no signup required.

---

## Features

### Core
- **Voice Dictation** -- Record directly from the browser with real-time waveform visualization
- **Audio Upload** -- Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG
- **Gemini Transcription** -- Structured entity extraction with Pydantic validation
- **Custom Billing Rates** -- Each user's hourly rate is dynamically applied

### Human-in-the-Loop (HITL)
- **Editable Review Form** -- Verify and correct client name, duration, matter, and amount before saving
- **Confidence Scoring** -- Visual confidence bar shows extraction accuracy
- **Approve or Discard** -- Nothing saves to the database until the user explicitly approves

### Authentication & Security
- **Supabase Auth** -- Email + password with session management
- **Row Level Security** -- Users only see their own billing data
- **POPIA Compliance** -- Audio files are scrubbed from Gemini immediately after extraction

### Dashboard & Pages
- **Dashboard Hub** -- Stat strip, recent entries, quick navigation to all features
- **Active Dictation** -- Bento-box layout with live waveform, transcription, and extraction sidebar
- **Review Entry** -- Editable form with entry preview, raw transcript, and confidence bar
- **Entry Detail** -- Full billing entry view with Source & Compliance grid, Fee Calculation (incl. VAT), and Audit Trail
- **Billing Ledger** -- Full history with clickable rows, export to CSV
- **FICA Compliance Report** -- Compliance checklist, risk assessment, and audit trail

### Design
- **Warm Cream Aesthetic** -- Premium legal-tech look (#FDFCF6 background, Playfair Display serif headings)
- **Bento Card Architecture** -- Clean white cards with soft borders, no glassmorphism
- **Tabular Numbers** -- All financial figures use tabular-nums for column alignment
- **PDF Invoice Generation** -- Branded invoices with jsPDF + autoTable

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Shadcn UI, Sonner, react-router-dom, jsPDF |
| **Backend** | Python, FastAPI, Uvicorn, httpx |
| **AI** | Google Gemini API (gemini-2.0-flash) |
| **Database** | Supabase (PostgreSQL + Row Level Security) |
| **Auth** | Supabase Auth (email + password) |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Architecture

```
LexFlow/
  main.py                    # FastAPI backend + Gemini + Supabase REST
  requirements.txt           # Python dependencies
  render.yaml                # Render deployment config
  frontend/
    src/
      App.tsx                 # Auth shell + route wiring
      pages/
        DashboardPage.tsx     # Hub: stats, CTAs, recent entries
        DictationPage.tsx     # Recording + waveform + extraction sidebar
        ReviewPage.tsx        # HITL review form + confidence bar
        EntryDetailPage.tsx   # Full entry detail + fee calc + audit trail
        FicaPage.tsx          # Compliance report + risk assessment
      components/
        lexflow/
          AuthPage.tsx        # Login / signup / onboarding / demo
          Navbar.tsx          # LEX⚖FLOW logo + nav links
          BillingLedger.tsx   # Ledger table with clickable rows
          MetricsStrip.tsx    # Reusable 4-column stat strip
          Breadcrumb.tsx      # Navigation breadcrumbs
          WaveformVisualizer.tsx  # Web Audio API waveform
          InvoiceGenerator.tsx    # PDF invoice (jsPDF + autoTable)
        ui/                   # Shadcn UI primitives
      lib/
        supabaseClient.ts     # Supabase browser client
        utils.ts              # Tailwind class merge
        formatters.ts         # ZAR currency & duration formatting
```

**Routes:**

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Stat strip, New Dictation CTA, recent entries |
| `/dictate` | Dictation | Live recording with waveform + extraction sidebar |
| `/review` | Review | Editable HITL form with confidence bar |
| `/entry/:id` | Entry Detail | Full detail with fee calc, audit trail |
| `/ledger` | Ledger | Billing table with export + invoice generation |
| `/fica` | Compliance | FICA report with checklist + risk assessment |

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
| **Bento layout over glassmorphism** | Premium legal aesthetic; cleaner, more professional |
| **Playfair Display serif** | Conveys authority and trust appropriate for legal tech |
| **react-router-dom** | Client-side routing for fast page transitions without full reloads |

---

## Development Journey

1. **Core Engine** -- FastAPI + Gemini transcription + Pydantic schema
2. **Structured Output** -- JSON extraction with retry logic
3. **Professional Dashboard** -- React SPA with Shadcn UI
4. **Supabase Integration** -- Auth, profiles, custom rates, RLS
5. **Human-in-the-Loop** -- Review form, toast notifications, POPIA compliance, demo mode
6. **Frontend Polish** -- Tabular numbers, stat strip, AI status dot, pipeline animation
7. **Route Architecture + PDF Invoices** -- Multi-page SPA, jsPDF invoice generation
8. **Frontend Redesign** -- Cream aesthetic, bento cards, serif headings, 6 dedicated pages

---

## License

MIT

## Author

**Tshepiso Jafta** -- [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
