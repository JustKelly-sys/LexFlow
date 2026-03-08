"""Pytest fixtures for LexFlow test suite."""
import os
import pytest

# Set env vars before any app imports
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
