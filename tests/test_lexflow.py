"""
LexFlow Test Suite

Tests core logic without requiring live Supabase or Gemini.
Uses FastAPI dependency_overrides for auth and httpx mock for DB calls.
"""
import io
import os
import csv
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from pydantic import ValidationError

os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")

from main import app, BillingEntry, TranscriptionResult, ALLOWED_AUDIO_EXTS, _build_prompt, get_current_user
from fastapi.testclient import TestClient


# ---- Fixtures ----

FAKE_USER = {"id": "test-user-123", "email": "test@lexflow.app", "token": "fake-jwt"}


def _override_auth():
    """Override the auth dependency for all tests that need it."""
    async def fake_user():
        return FAKE_USER
    app.dependency_overrides[get_current_user] = fake_user


def _clear_overrides():
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client():
    """TestClient with auth dependency overridden."""
    _override_auth()
    c = TestClient(app)
    yield c
    _clear_overrides()


@pytest.fixture
def client():
    """TestClient without auth override (for validation tests)."""
    return TestClient(app)


def _make_httpx_mock(**method_results):
    """Create a mock that replaces httpx.AsyncClient and returns prescribed responses.
    Usage: _make_httpx_mock(get=resp, post=resp)"""
    mock_inst = MagicMock()
    for method_name, resp in method_results.items():
        method_mock = AsyncMock(return_value=resp)
        setattr(mock_inst, method_name, method_mock)
    mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
    mock_inst.__aexit__ = AsyncMock(return_value=False)
    mock_constructor = MagicMock(return_value=mock_inst)
    return patch("main.httpx.AsyncClient", mock_constructor)


def _resp(status=200, data=None):
    """Fake httpx Response."""
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data if data is not None else []
    r.text = json.dumps(data if data is not None else [])
    return r


# ====================================================================
# 1. PYDANTIC SCHEMAS
# ====================================================================

class TestBillingEntry:
    def test_valid(self):
        e = BillingEntry(client_name="John", matter_description="NDA", duration="2h", billable_amount="R5000")
        assert e.client_name == "John"

    def test_dump_keys(self):
        e = BillingEntry(client_name="A", matter_description="B", duration="C", billable_amount="D")
        assert set(e.model_dump().keys()) == {"client_name", "matter_description", "duration", "billable_amount"}

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            BillingEntry(client_name="John", matter_description="Test")


class TestTranscriptionResult:
    def test_single(self):
        r = TranscriptionResult(
            entries=[BillingEntry(client_name="Jane", matter_description="Review", duration="1h", billable_amount="R2500")],
            confidence=0.92,
        )
        assert len(r.entries) == 1 and r.confidence == 0.92

    def test_multi(self):
        r = TranscriptionResult(
            entries=[
                BillingEntry(client_name="A", matter_description="X", duration="1h", billable_amount="R1000"),
                BillingEntry(client_name="B", matter_description="Y", duration="2h", billable_amount="R5000"),
            ],
            confidence=0.78,
        )
        assert len(r.entries) == 2 and r.entries[1].client_name == "B"

    def test_zero_confidence(self):
        r = TranscriptionResult(
            entries=[BillingEntry(client_name="A", matter_description="B", duration="C", billable_amount="D")],
            confidence=0.0,
        )
        assert r.confidence == 0.0


# ====================================================================
# 2. PROMPT BUILDER
# ====================================================================

class TestPromptBuilder:
    def test_contains_rate(self):
        p = _build_prompt(2500)
        assert "R2500" in p and "R5000" in p and "R1250" in p

    def test_custom_rate(self):
        p = _build_prompt(3500)
        assert "R3500" in p and "R7000" in p

    def test_multi_matter(self):
        assert "MULTIPLE" in _build_prompt(2500)

    def test_confidence(self):
        assert "confidence" in _build_prompt(2500).lower()


# ====================================================================
# 3. FILE VALIDATION
# ====================================================================

class TestFileValidation:
    def test_extensions(self):
        assert ALLOWED_AUDIO_EXTS == {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma"}

    def test_rejects_pdf(self, authed_client):
        r = authed_client.post("/transcribe", files={"file": ("test.pdf", b"fake", "application/pdf")})
        assert r.status_code == 400

    def test_rejects_exe(self, authed_client):
        r = authed_client.post("/transcribe", files={"file": ("bad.exe", b"fake", "application/octet-stream")})
        assert r.status_code == 400


# ====================================================================
# 4. BILLING ENDPOINTS
# ====================================================================

class TestBillingEndpoints:
    def test_missing_fields(self, authed_client):
        r = authed_client.post("/billing", json={"client_name": "John"})
        assert r.status_code == 400

    def test_save_success(self, authed_client):
        with _make_httpx_mock(post=_resp(201, [{"id": "1"}])):
            r = authed_client.post("/billing", json={
                "client_name": "John", "matter_description": "NDA",
                "duration": "2h", "billable_amount": "R5000",
            })
        assert r.status_code == 200 and r.json()["status"] == "saved"

    def test_get_empty(self, authed_client):
        with _make_httpx_mock(get=_resp(200, [])):
            r = authed_client.get("/billing")
        assert r.status_code == 200 and r.json()["count"] == 0

    def test_get_with_entries(self, authed_client):
        data = [{"client_name": "Jane", "duration": "1h", "billable_amount": "R2500",
                 "matter_description": "Review", "created_at": "2026-03-08"}]
        with _make_httpx_mock(get=_resp(200, data)):
            r = authed_client.get("/billing")
        assert r.json()["count"] == 1


# ====================================================================
# 5. CSV EXPORT
# ====================================================================

class TestCSVExport:
    def test_csv_output(self, authed_client):
        data = [{"created_at": "2026-03-08", "client_name": "Test Client",
                 "matter_description": "Test", "duration": "1 hour", "billable_amount": "R2500"}]
        with _make_httpx_mock(get=_resp(200, data)):
            r = authed_client.get("/billing/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        rows = list(csv.reader(io.StringIO(r.text)))
        assert "Client Name" in rows[0]
        assert "Test Client" in rows[1]


# ====================================================================
# 6. CORS
# ====================================================================

class TestCORS:
    def test_cors(self, client):
        r = client.options("/transcribe", headers={
            "Origin": "http://localhost:8000", "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" in r.headers


# ====================================================================
# 7. DELETE ENDPOINT
# ====================================================================

class TestDeleteEndpoint:
    def test_delete_success(self, authed_client):
        """DELETE /billing/:id should return 200 when entry exists and belongs to user."""
        with _make_httpx_mock(delete=_resp(204)):
            r = authed_client.delete("/billing/some-uuid-123")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    def test_delete_not_found(self, authed_client):
        """DELETE /billing/:id should return 404 when entry doesn't exist."""
        with _make_httpx_mock(delete=_resp(404)):
            r = authed_client.delete("/billing/nonexistent-id")
        assert r.status_code == 404

    def test_delete_requires_auth(self, client):
        """DELETE /billing/:id should require authentication."""
        r = client.delete("/billing/some-uuid-123")
        assert r.status_code in (401, 403)


# ====================================================================
# 8. INPUT VALIDATION
# ====================================================================

class TestInputValidation:
    def test_rejects_oversized_field(self, authed_client):
        """POST /billing should reject fields exceeding 2000 chars."""
        r = authed_client.post("/billing", json={
            "client_name": "A" * 2001,
            "matter_description": "NDA",
            "duration": "2h",
            "billable_amount": "R5000",
        })
        assert r.status_code == 400
        assert "exceeds maximum length" in r.json()["detail"]

    def test_rejects_empty_field(self, authed_client):
        """POST /billing should reject empty or whitespace-only fields."""
        r = authed_client.post("/billing", json={
            "client_name": "   ",
            "matter_description": "NDA",
            "duration": "2h",
            "billable_amount": "R5000",
        })
        assert r.status_code == 400
        assert "cannot be empty" in r.json()["detail"]

    def test_accepts_valid_fields(self, authed_client):
        """POST /billing should accept properly-sized fields."""
        with _make_httpx_mock(post=_resp(201, [{"id": "1"}])):
            r = authed_client.post("/billing", json={
                "client_name": "Valid Client",
                "matter_description": "Valid matter",
                "duration": "1.5h",
                "billable_amount": "R3750",
            })
        assert r.status_code == 200


# ====================================================================
# 9. CORS CONFIGURATION
# ====================================================================

class TestCORSConfig:
    def test_allowed_origin_localhost(self, client):
        """CORS should allow requests from localhost:8000."""
        r = client.options("/billing", headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        })
        assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"

    def test_allowed_origin_render(self, client):
        """CORS should allow requests from the Render deployment."""
        r = client.options("/billing", headers={
            "Origin": "https://lexflow-dwa0.onrender.com",
            "Access-Control-Request-Method": "POST",
        })
        assert r.headers.get("access-control-allow-origin") == "https://lexflow-dwa0.onrender.com"

    def test_disallowed_origin(self, client):
        """CORS should NOT allow requests from arbitrary origins."""
        r = client.options("/billing", headers={
            "Origin": "https://evil-site.com",
            "Access-Control-Request-Method": "GET",
        })
        # FastAPI CORS middleware won't set the header for disallowed origins
        origin = r.headers.get("access-control-allow-origin")
        assert origin is None or origin != "https://evil-site.com"
