"""
Supabase REST helpers — URL builders and header constructors.
"""
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY


def rest_url(path: str) -> str:
    """Full Supabase REST endpoint, e.g. 'billing_entries?...'"""
    return f"{SUPABASE_URL}/rest/v1/{path}"


def auth_url(path: str) -> str:
    """Full Supabase Auth endpoint, e.g. 'user'"""
    return f"{SUPABASE_URL}/auth/v1/{path}"


def headers(token: str | None = None) -> dict:
    """Standard headers — apikey is always the service key,
    but Authorization uses the user's JWT so RLS applies."""
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {token or SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def service_headers() -> dict:
    """Headers that bypass RLS — only for admin ops like demo wipe."""
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }
