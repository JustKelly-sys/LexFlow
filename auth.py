"""
Auth dependency — extracts + validates JWT on every request.
"""
import httpx
from fastapi import HTTPException, Request

from config import SUPABASE_SERVICE_KEY, HTTP_TIMEOUT
from services.supabase import auth_url


async def get_current_user(request: Request) -> dict:
    """Verify Bearer token against Supabase Auth; return user dict or raise 401."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")

    token = auth.removeprefix("Bearer ")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            auth_url("user"),
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {token}"},
        )

    if res.status_code != 200:
        raise HTTPException(401, "Invalid or expired token")
    return {**res.json(), "token": token}
