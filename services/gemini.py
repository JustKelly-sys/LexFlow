"""
Gemini AI extraction — structured billing data from audio.
"""
import json
import time

import httpx
from google import genai
from pydantic import BaseModel

from config import API_KEY, MODEL_NAME, MAX_RETRIES, RETRY_BASE_DELAY, DEFAULT_RATE, HTTP_TIMEOUT
from services.supabase import rest_url, headers


# ── Schema
class BillingEntry(BaseModel):
    client_name: str
    matter_description: str
    duration: str
    billable_amount: str


class TranscriptionResult(BaseModel):
    """Wrapper for multi-matter extraction + AI confidence score."""
    entries: list[BillingEntry]
    confidence: float  # 0.0-1.0


def extract_billing(client: genai.Client, audio_ref, model: str, prompt: str) -> TranscriptionResult:
    """Call Gemini with structured output. Returns multiple entries + confidence.
    Retries on 429 with exponential backoff.

    WARNING: Uses blocking time.sleep(). Must be called via asyncio.to_thread()."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[audio_ref, prompt],
                config={"response_mime_type": "application/json", "response_schema": TranscriptionResult},
            )
            if response.parsed:
                return response.parsed
            return TranscriptionResult(**json.loads(response.text))

        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" not in msg and "quota" not in msg:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[Gemini] 429 — retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(delay)

    raise RuntimeError(f"Gemini extraction failed after {MAX_RETRIES} retries: {last_err}")


def build_prompt(hourly_rate: int) -> str:
    """Build the extraction prompt with the user's hourly rate baked in."""
    return (
        f"You are a legal billing assistant for a South African law firm. "
        f"The attorney's hourly rate is R{hourly_rate:,}. "
        f"Listen to this voice note and extract structured billing information.\n\n"
        f"For EACH distinct matter mentioned, extract:\n"
        f"- client_name: The client or entity (use 'Unspecified Client' if unclear)\n"
        f"- matter_description: Detailed description of legal work performed\n"
        f"- duration: Estimated time spent in hours and minutes (e.g., '2 hours', '45 minutes')\n"
        f"- billable_amount: Calculated as duration × hourly rate of R{hourly_rate:,}/hr, "
        f"formatted as 'RXXXX' (Rands only, no cents)\n\n"
        f"Also provide a 'confidence' score (0.0 to 1.0) indicating how confident you "
        f"are in the overall extraction accuracy. Lower confidence if audio is unclear, "
        f"names are ambiguous, or durations are estimated.\n\n"
        f"Return valid JSON matching the schema. Every field must be non-empty."
    )


async def get_hourly_rate(user: dict) -> int:
    """Fetch attorney's hourly rate from profile. Returns DEFAULT_RATE if missing."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(
            rest_url(f"profiles?id=eq.{user['id']}&select=hourly_rate"),
            headers=headers(user["token"]),
        )
    if res.status_code != 200 or not res.json():
        return DEFAULT_RATE
    return res.json()[0].get("hourly_rate", DEFAULT_RATE)
