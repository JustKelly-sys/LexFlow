# LexFlow

**Billing Intelligence Platform for Legal Professionals**

**[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing intelligence platform built for South African attorneys and law firms. Attorneys dictate or upload a voice note describing their work, and LexFlow autonomously transcribes it with Gemini AI, extracts structured billing entities (client name, matter description, duration), calculates the billable amount at R2,500/hr, and generates FICA-compliant ledger entries ready for invoicing.

---

## How It Works

1. **Dictate or Upload** -- Record a voice note directly in the browser or drag-and-drop an audio file onto the dashboard
2. **AI Extraction** -- Gemini AI transcribes the audio, identifies the client entity, matter description, estimated duration, and calculates the billable amount in ZAR
3. **Ledger Entry** -- A structured billing record is saved to the ledger and displayed in real time on the executive dashboard

---

## Demo Example

Showcase how LexFlow moves beyond simple transcription to contextual billing logic:

**Input File:** [JonesLegal.mp3 (Legal Interview Summary)](https://www.nch.com.au/scribe/practice/JonesLegal.mp3)

**LexFlow Smart Output:**
- **Time Entry:** 0.8 hours (approx. based on narration length/complexity)
- **Description:** "Initial client interview and drafting of detailed case summary regarding workplace injury claim: Matter of Henry Jones."
- **Category:** Professional Consultation / Case Assessment

LexFlow identifies the Client Name (Henry Jones), the Matter Type (Personal Injury / Workman's Comp), and the Action (Interview/Summary) -- all from a single audio file.

---

## Features

- **Voice Dictation** -- Record directly from the browser with one click
- **Drag-and-Drop Upload** -- Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG
- **Gemini AI Transcription** -- Structured entity extraction with Pydantic validation
- **Automatic ZAR Billing** -- Calculates billable amounts at R2,500/hr
- **Executive Dashboard** -- Real-time metrics for total hours billed and ZAR revenue
- **Billing Ledger** -- Full history with client, matter, duration, and amount columns
- **FICA-Compliant CSV Export** -- One-click download for accounting software integration
- **Retry Logic** -- Exponential backoff on API rate limits for production reliability

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Shadcn UI, Framer Motion |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI** | Google Gemini API (gemini-2.0-flash) |
| **Data** | CSV storage with structured export |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Architecture

```
LexFlow/
  main.py              # FastAPI backend + Gemini AI integration
  requirements.txt     # Python dependencies
  render.yaml          # Render deployment config
  frontend/
    src/
      App.tsx           # Main application shell
      components/
        lexflow/        # Feature components
          Navbar.tsx
          AudioUploader.tsx
          ExecutiveMetrics.tsx
          BillingLedger.tsx
        ui/             # Shadcn UI primitives
      lib/
        utils.ts        # Tailwind class merge utility
        formatters.ts   # ZAR currency & duration formatting
    vite.config.ts      # Vite + Tailwind CSS v4 config
    tailwind.config.js  # Design tokens & theme
```

The FastAPI backend serves the compiled React build via StaticFiles. API endpoints (`/transcribe`, `/billing`, `/billing/csv`) are registered before the SPA catch-all route to ensure correct routing.

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

# Set up environment variables
# Create a .env file with:
# GOOGLE_API_KEY=your_api_key_here

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` to access the dashboard.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Executive billing dashboard (React SPA) |
| POST | `/transcribe` | Upload voice note for AI billing extraction |
| GET | `/billing` | Get all billing entries as JSON |
| GET | `/billing/csv` | Download FICA-compliant billing CSV |

---

## Deployment

LexFlow is configured for one-click deployment on [Render](https://render.com):

1. Fork this repo
2. Connect your GitHub account to Render
3. Create a new **Web Service** pointing to the repo
4. Set the environment variable `GOOGLE_API_KEY` in the Render dashboard
5. Deploy -- Render reads `render.yaml`, builds both the React frontend and Python backend automatically

The free tier sleeps after 15 minutes of inactivity but wakes up automatically on the next request.

---

## Development Journey

**Phase 1: Core Transcription Engine** -- Built a FastAPI endpoint that accepts audio files, sends them to Gemini for transcription, and extracts structured billing data using a custom prompt.

**Phase 2: Structured Output and Data Persistence** -- Replaced free-text parsing with Pydantic schema validation and Gemini's structured JSON output. Added CSV-based storage for billing record persistence.

**Phase 3: Rate Limiting and Reliability** -- Implemented exponential backoff retry logic to handle Gemini API rate limits (429 errors) gracefully.

**Phase 4: Professional Dashboard** -- Evolved from an embedded HTML dashboard through several design iterations to a full React SPA with Shadcn UI components, fluted-glass visual effects, and Framer Motion animations.

**Phase 5: Firebase Studio UI and Integration** -- Designed the final "Voice Intelligence Simplified" interface in Firebase Studio with a premium legal-tech aesthetic, then migrated it into the local Vite/React project with full backend connectivity.

---

## License

MIT

## Author

**Tshepiso Jafta** -- [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
