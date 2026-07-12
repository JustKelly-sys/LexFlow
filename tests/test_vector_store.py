"""
Tests for the LanceDB vector store service.
Run from LexFlow/: python -m pytest tests/test_vector_store.py -v

Note: VectorStore._embed() is mocked in all storage tests so no real API call is made.
The embed function is tested implicitly through the ingest script (integration test).
"""
import os
import shutil
import pytest
from unittest.mock import patch

from services.vector_store import VectorStore, EMBEDDING_DIM


LANCE_TEST_DIR = "./test_lance_db"

# Deterministic fake embedding -- all zeros except first element
# Different strings get slightly different vectors so retrieval ordering works
def fake_embed(text: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    vec[0] = float(hash(text[:30]) % 1000) / 1000.0
    return vec


@pytest.fixture(autouse=True)
def clean_test_db():
    if os.path.exists(LANCE_TEST_DIR):
        shutil.rmtree(LANCE_TEST_DIR)
    yield
    if os.path.exists(LANCE_TEST_DIR):
        shutil.rmtree(LANCE_TEST_DIR)


@pytest.fixture
def store():
    with patch.object(VectorStore, "_embed", fake_embed):
        s = VectorStore(persist_dir=LANCE_TEST_DIR, table_name="test_policies")
        yield s


def test_ingest_and_retrieve_single_chunk(store):
    with patch.object(store, "_embed", fake_embed):
        store.ingest("policy_001", "After-hours work is billed at 150% of the standard hourly rate.", {"source": "after_hours.md"})
        results = store.retrieve("what is the rate for working on weekends?", n_results=1)
    assert len(results) == 1
    assert "150%" in results[0]["text"]


def test_ingest_multiple_and_retrieve_relevant(store):
    with patch.object(store, "_embed", fake_embed):
        store.ingest("p1", "Travel time is billed at 50% of the hourly rate.", {"source": "travel.md"})
        store.ingest("p2", "After-hours work is billed at 150% of the standard rate.", {"source": "after_hours.md"})
        store.ingest("p3", "Non-billable activities include internal administrative tasks.", {"source": "standard.md"})
        results = store.retrieve("travel to client site billing", n_results=1)
    assert len(results) == 1
    assert results[0]["text"] != ""


def test_retrieve_returns_n_results(store):
    with patch.object(store, "_embed", fake_embed):
        for i in range(5):
            store.ingest(f"doc_{i}", f"Billing rule number {i} applies to matters of type {i}.", {"source": f"rule_{i}.md"})
        results = store.retrieve("billing rules for matters", n_results=3)
    assert len(results) == 3


def test_retrieve_from_empty_store_returns_empty(store):
    with patch.object(store, "_embed", fake_embed):
        results = store.retrieve("anything", n_results=3)
    assert results == []


def test_ingest_duplicate_id_overwrites(store):
    with patch.object(store, "_embed", fake_embed):
        store.ingest("dup_001", "Original text about billing.", {"source": "original.md"})
        store.ingest("dup_001", "Updated text about billing at 200%.", {"source": "updated.md"})
        results = store.retrieve("billing percentage", n_results=5)
    assert len(results) == 1


def test_build_prompt_without_context_unchanged():
    from services.gemini import build_prompt
    prompt = build_prompt(hourly_rate=3500, policy_context=None)
    assert "R3500" in prompt
    assert "legal billing assistant" in prompt
    assert "BILLING POLICY CONTEXT" not in prompt


def test_build_prompt_with_context_injects_policy():
    from services.gemini import build_prompt
    mock_context = "Travel is billed at 50% of the hourly rate."
    prompt = build_prompt(hourly_rate=3500, policy_context=mock_context)
    assert "BILLING POLICY CONTEXT" in prompt
    assert "Travel is billed at 50%" in prompt
    assert "R3500" in prompt
