# LexFlow

**Billing Intelligence Platform for Legal Professionals**

**[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing intelligence platform built for South African attorneys and law firms. Dictate or upload a voice note, and LexFlow autonomously transcribes it with Gemini AI, extracts structured billing entities, calculates the billable amount at your custom hourly rate, and generates FICA-compliant ledger entries — all scoped to your authenticated profile.

---

## How It Works

1. **Sign Up** — Create an account with your email and set your custom hourly rate (ZAR)
2. **Dictate or Upload** — Record a voice note in-browser or drag-and-drop an audio file
3. **AI Extraction** — Gemini AI transcribes the audio, identifies client, matter, duration, and calculates your billable amount
4. **Ledger Entry** — A structured billing record is saved to your personal ledger with Row Level Security

---

## Features

- **User Authentication** — Email + password auth via Supabase with session management
- **Onboarding Flow** — First-time setup with name, firm, and custom hourly rate
- **Custom Billing Rates** — Each user's hourly rate is dynamically passed to the AI prompt
- **Row Level Security** — Users only see their own billing data
- **Voice Dictation** — Record directly from the browser with one click
- **Drag-and-Drop Upload** — Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG
- **Gemini AI Transcription** — Structured entity extraction with Pydantic validation
- **Executive Dashboard** — Real-time metrics for total hours billed and ZAR revenue
- **Billing Ledger** — Full history with client, matter, duration, and amount columns
- **FICA-Compliant CSV Export** — One-click download for accounting software integration
- **Retry Logic** — Exponential backoff on API rate limits for production reliability

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Shadcn UI |
| **Backend** | Python, FastAPI, Uvicorn, httpx |
| **AI** | Google Gemini API (gemini-2.0-flash) |
| **Database** | Supabase (PostgreSQL with Row Level Security) |
| **Auth** | Supabase Auth (email + password) |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Architecture

```
LexFlow/
  main.py                # FastAPI backend + Gemini AI + Supabase REST
  requirements.txt       # Python dependencies
  render.yaml            # Render deployment config
  frontend/
    src/
      App.tsx             # Main app shell with auth state management
      components/
        lexflow/          # Feature components
          AuthPage.tsx    # Login / signup / onboarding
          Navbar.tsx      # User info + logout
          AudioUploader.tsx
          ExecutiveMetrics.tsx
          BillingLedger.tsx
        ui/               # Shadcn UI primitives
      lib/
        supabaseClient.ts # Supabase browser client
        utils.ts          # Tailwind class merge utility
        formatters.ts     # ZAR currency & duration formatting
    vite.config.ts        # Vite + Tailwind CSS v4 config
    tailwind.config.js    # Design tokens & theme
```

The FastAPI backend communicates with Supabase via httpx REST calls. Auth tokens from the frontend are forwarded to Supabase for Row Level Security enforcement. API endpoints are registered before the SPA catch-all route.

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/JustKelly-sys/LexFlow.git
cd LexFlow

# Backend setup
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
npm run build
cd ..

# Environment variables (.env file)
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` to sign up and access the dashboard.

---

## API Endpoints

All endpoints except the frontend require a valid `Authorization: Bearer <token>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | React SPA (login / dashboard) |
| POST | `/transcribe` | Upload voice note for AI billing extraction |
| GET | `/billing` | Get authenticated user's billing entries |
| GET | `/billing/csv` | Download billing data as CSV |
| GET | `/profile` | Get authenticated user's profile |
| PATCH | `/profile` | Update profile (name, firm, rate) |

---

## Deployment

LexFlow is configured for one-click deployment on [Render](https://render.com):

1. Fork this repo
2. Connect your GitHub account to Render
3. Create a new **Web Service** pointing to the repo
4. Set environment variables in the Render dashboard:
   - `GOOGLE_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `NODE_VERSION=20`
5. Deploy — Render reads `render.yaml` and builds both frontend and backend automatically

---

## Development Journey

**Phase 1: Core Transcription Engine** — FastAPI endpoint accepting audio files, Gemini transcription, and structured billing extraction.

**Phase 2: Structured Output** — Pydantic schema validation with Gemini's JSON output. CSV-based storage for billing records.

**Phase 3: Reliability** — Exponential backoff retry logic for Gemini API rate limits.

**Phase 4: Professional Dashboard** — Full React SPA with Shadcn UI, fluted-glass effects, and a premium legal-tech aesthetic.

**Phase 5: Firebase Studio UI** — Designed the "Voice Intelligence Simplified" interface in Firebase Studio, then migrated to local Vite/React.

**Phase 6: Supabase Integration** — Migrated from CSV to Supabase Postgres. Added user authentication, per-user billing profiles with custom hourly rates, and Row Level Security.

---

## License

MIT

## Author

**Tshepiso Jafta** — [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
