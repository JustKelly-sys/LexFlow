# LexFlow

**Billing Intelligence Platform for Legal Professionals**

**[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing intelligence platform built for South African legal professionals. Dictate via WhatsApp or the web app, and LexFlow transcribes it with Google Gemini, extracts structured billing entities, and presents an editable review form for human verification before committing to your personal ledger -- all scoped to your authenticated profile with Row Level Security.

---

## How It Works

### Web App
1. **Sign Up** -- Create an account with your email and set your custom hourly rate (ZAR)
2. **Dictate or Upload** -- Record a voice note in-browser or upload an audio file
3. **Review & Approve** -- Extracted billing data appears in an editable form for human verification
4. **Ledger Entry** -- Approved records are saved to your personal billing ledger

### WhatsApp
1. **Send a message** -- Text or voice note to the LexFlow WhatsApp number
2. **Set your rate** -- Reply with your hourly billing rate on first use
3. **Send a voice note** -- Describe your billable work naturally
4. **Approve or reject** -- Reply YES, NO, or EDIT to the extracted entry
5. **Link your account** -- Type LINK to connect WhatsApp to your web dashboard

> **Recruiters:** Click **"Try Demo"** on the login page -- no signup required.

---

## Features

### Core Pipeline
- **Voice Dictation** -- Record directly from the browser with real-time waveform visualization
- **Audio Upload** -- Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG
- **Gemini Extraction** -- Structured entity extraction (client name, matter, duration, amount) with Pydantic validation
- **Custom Billing Rates** -- Each user's hourly rate is dynamically applied during extraction

### WhatsApp Integration
- **Voice Notes** -- Send a voice note describing your billable work; Gemini extracts billing data automatically
- **Conversational Approval** -- Reply YES to save, NO to discard, or EDIT to modify on web
- **Onboarding Flow** -- New users are greeted with a brief explanation and prompted to set their hourly rate
- **Account Linking** -- Type LINK to get a code that connects WhatsApp to your web dashboard
- **State Machine** -- Tracks user state (NEW → AWAITING_RATE → READY → AWAITING_APPROVAL) for clean conversation flow
- **Meta Cloud API** -- Uses the free tier (1,000 conversations/month) for zero-cost messaging
- **POPIA Compliance** -- Voice notes are downloaded, processed, and immediately deleted

### Human-in-the-Loop (HITL)
- **Editable Review Form** -- Verify and correct all fields before saving (web)
- **WhatsApp Approval** -- YES / NO / EDIT responses for mobile approval
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
- **Review Entry** -- HITL review form with live entry preview and confidence bar
- **Entry Detail** -- Full billing entry view with stable reference numbers and working delete
- **Billing Ledger** -- Full history with clickable rows, CSV export, PDF invoice generation
- **Data Quality Report** -- Analyses billing data completeness (client ID rate, description quality, duration accuracy)
- **WhatsApp Link** -- Sign in or create an account to connect your WhatsApp number

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
| **Messaging** | Meta Cloud API (WhatsApp Business) |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Architecture

```
LexFlow/
  main.py                    # FastAPI backend + Gemini + Supabase + WhatsApp webhook
  requirements.txt           # Python dependencies (pinned)
  render.yaml                # Render deployment config + env vars
  tests/
    test_lexflow.py           # 28 tests: schemas, CRUD, CORS, validation
  frontend/
    src/
      App.tsx                 # Auth shell + route wiring + WhatsApp link handler
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
        WhatsAppLinkPage.tsx  # Account linking (sign in / create account + auto-link)
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
| `/whatsapp/link/:code` | WhatsApp Link | Sign in or sign up to connect WhatsApp to web account |

**Data Flow:**

```
Web:      Browser → FastAPI → Gemini (extract) → User Review (HITL) → Supabase (save) → Dashboard
WhatsApp: Phone → Meta Cloud API → FastAPI webhook → Gemini (extract) → WhatsApp reply → User approves → Supabase (save)
```

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
WHATSAPP_TOKEN=your_meta_cloud_api_token
WHATSAPP_PHONE_ID=your_whatsapp_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_custom_webhook_token

# Run
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### WhatsApp Setup

1. Create a Meta Developer App at [developers.facebook.com](https://developers.facebook.com)
2. Add the WhatsApp product and get a test phone number
3. Set the webhook URL to `https://your-domain.com/webhook`
4. Subscribe to the `messages` webhook field
5. Add your personal number to the allowed list for testing
6. Set the env vars in `.env` and Render dashboard

---

## API Endpoints

All endpoints except the frontend and webhook require `Authorization: Bearer <token>`.

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
| GET | `/webhook` | Meta webhook verification (challenge-response) |
| POST | `/webhook` | Receive WhatsApp messages (voice notes, text) |
| POST | `/whatsapp/link` | Link WhatsApp number to web account via code |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI over Django** | Async-first -- handles Gemini API latency without blocking |
| **Supabase over Firebase** | Postgres + Row Level Security + built-in auth REST API |
| **httpx over supabase-py** | Avoids C-extension build failures on Windows/Render |
| **HITL over auto-save** | Legal billing demands accuracy -- AI extraction is a draft, not a fact |
| **WhatsApp over custom mobile app** | Legal professionals already use WhatsApp daily; zero adoption friction |
| **Meta Cloud API free tier** | 1,000 conversations/month at R0 cost -- ideal for portfolio and early users |
| **State machine for chat** | Clean conversation flow without ambiguous states or race conditions |
| **Bento layout** | Premium legal aesthetic; cleaner and more professional |
| **Playfair Display serif** | Conveys authority and trust appropriate for legal tech |

---

## Database Schema

### `billing_entries`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| user_id | UUID | FK to auth.users (nullable for unlinked WhatsApp entries) |
| client_name | TEXT | Extracted or manually entered |
| matter_description | TEXT | Work description |
| duration | TEXT | e.g. "2 hours" |
| billable_amount | TEXT | e.g. "R5,064" |
| source | TEXT | `web` or `whatsapp` |
| created_at | TIMESTAMPTZ | Auto-generated |

### `whatsapp_users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| phone | TEXT | WhatsApp number (unique) |
| user_id | UUID | FK to auth.users (set when linked) |
| hourly_rate | INTEGER | Billing rate in ZAR |
| state | TEXT | NEW, AWAITING_RATE, READY, AWAITING_APPROVAL |
| pending_entry | JSONB | Entry awaiting user approval |
| link_code | TEXT | Code for account linking |

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
