"""
Profile endpoints — read and update the authenticated user's profile.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import get_current_user
from config import HTTP_TIMEOUT
from services.supabase import headers, rest_url

router = APIRouter()


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile row."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url(f"profiles?id=eq.{user['id']}&select=*"),
            headers=headers(user["token"]),
        )
    if res.status_code == 200 and res.json():
        return JSONResponse(content=res.json()[0])
    raise HTTPException(404, "Profile not found")


@router.patch("/profile")
async def update_profile(request: Request, user: dict = Depends(get_current_user)):
    """Update profile fields (onboarding, rate changes). Whitelist-filtered."""
    body = await request.json()
    allowed = {"full_name", "firm_name", "phone", "hourly_rate", "onboarded"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(400, "No valid fields to update")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.patch(
            rest_url(f"profiles?id=eq.{user['id']}"),
            headers=headers(user["token"]),
            json=update,
        )
    if res.status_code not in (200, 204):
        raise HTTPException(500, f"Failed to update profile: {res.text}")
    try:
        data = res.json() if res.text else None
        if data:
            return JSONResponse(content=data[0])
    except (ValueError, IndexError):
        pass
    return JSONResponse(content={"status": "updated"})
