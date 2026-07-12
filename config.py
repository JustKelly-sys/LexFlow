"""
LexFlow — Configuration

All environment variables and constants loaded once at startup.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("lexflow")

# ── Core
API_KEY              = os.getenv("GOOGLE_API_KEY")
# Default must be a model with live free-tier quota: gemini-2.0-flash now
# returns 429 "limit: 0" on free keys (verified 2026-07-12)
MODEL_NAME           = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY    = os.getenv("SUPABASE_ANON_KEY") or SUPABASE_SERVICE_KEY

# ── Deployment
APP_ENV = os.getenv("APP_ENV", "development")   # "development" | "production"
APP_URL = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")

# ── Paths & limits
BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST      = os.path.join(BASE_DIR, "frontend", "dist")
LANCE_DB_DIR       = os.getenv("LANCE_DB_DIR", os.path.join(BASE_DIR, "lance_db"))
POLICY_DOCS_DIR    = os.path.join(BASE_DIR, "data", "billing_policies")
ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}
MAX_AUDIO_BYTES    = 25 * 1024 * 1024   # Gemini Files API hard limit
MAX_RETRIES        = 3
RETRY_BASE_DELAY   = 5
DEMO_EMAIL         = "demo@lexflow.app"
DEFAULT_RATE       = 2500
HTTP_TIMEOUT       = 15.0
CONFIDENCE_THRESHOLD = 0.7

# ── WhatsApp Cloud API
WHATSAPP_TOKEN       = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "lexflow-verify-2026")
WHATSAPP_APP_SECRET  = os.getenv("WHATSAPP_APP_SECRET", "")
GRAPH_API_URL        = "https://graph.facebook.com/v21.0"

# ── Startup warnings
if not API_KEY:
    log.warning("GOOGLE_API_KEY not set — /transcribe will fail.")
if not SUPABASE_URL:
    log.warning("SUPABASE_URL not set — all DB calls will fail.")
if APP_ENV == "production" and WHATSAPP_TOKEN and not WHATSAPP_APP_SECRET:
    log.warning(
        "WHATSAPP_APP_SECRET not set in production — "
        "incoming webhooks will be REJECTED until it is configured."
    )
