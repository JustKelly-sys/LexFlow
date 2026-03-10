"""
LexFlow — Configuration

All environment variables and constants loaded once at startup.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Core
API_KEY              = os.getenv("GOOGLE_API_KEY")
MODEL_NAME           = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ── Paths & limits
FRONTEND_DIST      = os.path.join(os.path.dirname(__file__), "frontend", "dist")
ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}
MAX_RETRIES        = 3
RETRY_BASE_DELAY   = 5
DEMO_EMAIL         = "demo@lexflow.app"
DEFAULT_RATE       = 2500
HTTP_TIMEOUT       = 15.0

# ── WhatsApp Cloud API
WHATSAPP_TOKEN       = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "lexflow-verify-2026")
WHATSAPP_APP_SECRET  = os.getenv("WHATSAPP_APP_SECRET", "")
GRAPH_API_URL        = "https://graph.facebook.com/v21.0"

# ── Startup warnings
if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not set — /transcribe will fail.")
if not SUPABASE_URL:
    print("WARNING: SUPABASE_URL not set — all DB calls will fail.")
