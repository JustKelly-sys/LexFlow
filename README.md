# LexFlow

**Billing Intelligence Platform for Legal Professionals**
?? **[Live Demo](https://lexflow-dwa0.onrender.com)**

LexFlow is a voice-to-billing tool built for attorneys and law firms. Attorneys send a voice note describing their work, and LexFlow automatically transcribes it, extracts billing details, and generates structured billing entries ready for invoicing.

## How It Works

1. **Record** — Attorney sends a voice note via the API describing the work they did
2. **Transcribe** — Gemini AI processes the audio and extracts client name, matter description, duration, and calculates the billable amount
3. **Bill** — A structured billing entry is saved and displayed on the live dashboard


## 💡 Pro-Tip for your GitHub Demo

Showcase how LexFlow moves beyond simple transcription to contextual billing logic. Try uploading this sample file:

**Input File:** [JonesLegal.mp3 (Legal Interview Summary)](https://www.nch.com.au/scribe/practice/JonesLegal.mp3)

**LexFlow Smart Output:**
- **Time Entry:** 0.8 hours *(approx. based on narration length/complexity)*
- **Description:** "Initial client interview and drafting of detailed case summary regarding workplace injury claim: Matter of Henry Jones."
- **Category:** Professional Consultation / Case Assessment

*(Notice how LexFlow identifies the Client Name "Henry Jones", the Matter Type "Personal Injury / Workman's Comp", and the Action "Interview/Summary")*

## Development Journey

This project went through several iterations before reaching its current form:

### Phase 1: Core Transcription Engine
Started with the fundamental problem: attorneys lose billable hours because manual time-tracking is tedious. Built a basic FastAPI endpoint that accepts audio files, sends them to the Gemini API for transcription, and extracts structured billing data using a custom prompt.

### Phase 2: Structured Output & Data Persistence
Replaced free-text parsing with Pydantic schema validation and Gemini's structured JSON output. Added CSV-based storage so billing entries persist between sessions and can be exported directly into accounting software.

### Phase 3: Rate Limiting & Reliability
Ran into Gemini API rate limits (429 errors) during testing with multiple voice notes. Implemented exponential backoff retry logic with configurable max retries and base delay, making the system production-ready.

### Phase 4: Live Dashboard (v1)
Built an embedded HTML dashboard served at the root URL. First version used a dark gradient tech aesthetic with neon accents. Functional but didn't match the professional tone of a legal billing tool.

### Phase 5: LexFlow Rebrand & Professional UI
Rebranded from "Voice-to-Bill" to "LexFlow". Completely redesigned the dashboard with a legal publishing aesthetic inspired by LexisNexis and Juta: serif typography (Libre Baskerville), navy/burgundy/gold palette, warm parchment backgrounds, and clean tabular data presentation. The result is a tool that looks like it belongs in a law firm.

## Features

- Voice note transcription via Gemini AI
- Automatic billable amount calculation (ZAR)
- Live billing dashboard with real-time auto-refresh
- CSV export for integration with accounting software
- Built-in retry logic for API rate limiting
- Structured JSON output with Pydantic validation

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Google Gemini API (gemini-2.0-flash)
- **Frontend:** Vanilla HTML/CSS/JS (embedded dashboard)
- **Data:** CSV storage with structured export

## Getting Started

```bash
# Clone the repo
git clone https://github.com/JustKelly-sys/LexFlow.git
cd LexFlow

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create a .env file with:
# GOOGLE_API_KEY=your_api_key_here

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Live billing dashboard |
| POST | `/transcribe` | Upload voice note for billing extraction |
| GET | `/billing` | Get all billing entries as JSON |
| GET | `/billing/csv` | Download billing data as CSV |

## Deployment

LexFlow is configured for one-click deployment on [Render](https://render.com):

1. Fork this repo
2. Connect your GitHub account to Render
3. Create a new **Web Service** pointing to the repo
4. Set the environment variable `GOOGLE_API_KEY` in the Render dashboard
5. Deploy — Render will auto-detect `render.yaml` and handle the rest

The free tier sleeps after 15 minutes of inactivity but wakes up automatically on the next request.

## License

MIT

## Author

**Tshepiso Jafta** — [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)


