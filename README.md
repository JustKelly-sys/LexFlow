# LexFlow

**Billing Intelligence Platform for Legal Professionals**

LexFlow is a voice-to-billing tool built for attorneys and law firms. Attorneys send a voice note describing their work, and LexFlow automatically transcribes it, extracts billing details, and generates structured billing entries ready for invoicing.

## How It Works

1. **Record** - Attorney sends a voice note via the API describing the work they did
2. **Transcribe** - Gemini AI processes the audio and extracts client name, matter description, duration, and calculates the billable amount
3. **Bill** - A structured billing entry is saved and displayed on the live dashboard

## Features

- Voice note transcription via Gemini AI
- Automatic billable amount calculation (ZAR)
- Live billing dashboard with real-time updates
- CSV export for integration with accounting software
- Built-in retry logic for API rate limiting

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI:** Google Gemini API (gemini-2.0-flash)
- **Frontend:** Vanilla HTML/CSS/JS (embedded dashboard)
- **Data:** CSV storage with structured export

## Getting Started

`ash
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
`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Live billing dashboard |
| POST | `/transcribe` | Upload voice note for billing extraction |
| GET | `/billing` | Get all billing entries as JSON |
| GET | `/billing/csv` | Download billing data as CSV |

## Screenshot

The LexFlow dashboard provides a clean, professional view of all billing entries with summary statistics.

## License

MIT

## Author

**Tshepiso Jafta** - [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
