"""
Supabase REST helpers — URL builders and header constructors.

Two header modes, kept deliberately separate:
- headers(token): user-scoped — RLS applies via the user's JWT.
- service_headers(): RLS bypass — admin/webhook operations only.
"""
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY


def rest_url(path: str) -> str:
    """Full Supabase REST endpoint, e.g. 'billing_entries?...'"""
    return f"{SUPABASE_URL}/rest/v1/{path}"


def auth_url(path: str) -> str:
    """Full Supabase Auth endpoint, e.g. 'user'"""
    return f"{SUPABASE_URL}/auth/v1/{path}"


def headers(token: str) -> dict:
    """User-scoped headers. The apikey is the anon key (gateway pass);
    Authorization carries the user's JWT so RLS applies.

    token is required — RLS bypass must go through service_headers()
    explicitly, never by accidentally omitting an argument.
    """
    if not token:
        raise ValueError("headers() requires a user JWT; use service_headers() for admin ops")
    return {
        "apikey":        SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def service_headers(prefer: str = "return=minimal") -> dict:
    """Headers that bypass RLS — only for webhook and demo-seed operations.

    Pass prefer="return=representation" when the caller needs the row back
    (e.g. creating a whatsapp_users record).
    """
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        prefer,
    }
