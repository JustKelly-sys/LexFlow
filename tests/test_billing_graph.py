"""Tests for the LangGraph billing pipeline."""
import pytest
from unittest.mock import MagicMock, patch
from services.billing_graph import (
    BillingState,
    CONFIDENCE_THRESHOLD,
    node_classify_billable,
    node_retrieve_context,
    build_billing_graph,
    run_billing_graph,
)


# ── Task 1: State schema ─────────────────────────────────────────────

def test_billing_state_has_required_keys():
    """BillingState must carry all pipeline data from node to node."""
    state: BillingState = {
        "audio_ref": None,
        "hourly_rate": 2500,
        "policy_context": None,
        "raw_text": "",
        "is_billable": None,
        "entries": [],
        "confidence": 0.0,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    assert state["hourly_rate"] == 2500
    assert state["needs_human_review"] is False
    assert isinstance(state["entries"], list)


def test_confidence_threshold_value():
    assert CONFIDENCE_THRESHOLD == 0.7


# ── Task 2: Node tests ───────────────────────────────────────────────

def test_node_classify_billable_defaults_to_billable_on_error():
    """When Gemini call fails, classifier should fail open (True)."""
    state: BillingState = {
        "audio_ref": MagicMock(),
        "hourly_rate": 2500,
        "policy_context": None,
        "raw_text": "client consultation merger agreement two hours",
        "is_billable": None,
        "entries": [],
        "confidence": 0.0,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    with patch("services.billing_graph._genai") as mock_genai:
        mock_genai.Client.side_effect = Exception("Simulated API failure")
        result = node_classify_billable(state)
    assert result["is_billable"] is True
    assert len(result["audit_log"]) >= 1


def test_node_retrieve_context_returns_none_when_no_store():
    """If vector store is unavailable, policy_context stays None — no crash."""
    state: BillingState = {
        "audio_ref": None,
        "hourly_rate": 2500,
        "policy_context": None,
        "raw_text": "after hours weekend",
        "is_billable": True,
        "entries": [],
        "confidence": 0.0,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    with patch("services.billing_graph._VECTOR_STORE", None):
        result = node_retrieve_context(state)
    assert result["policy_context"] is None


# ── Task 3: Graph wiring ─────────────────────────────────────────────

def test_build_billing_graph_returns_compiled_graph():
    """Graph must compile without error."""
    graph = build_billing_graph()
    assert graph is not None


def test_graph_has_human_review_and_log_result_nodes():
    """Graph must expose both terminal nodes."""
    graph = build_billing_graph()
    assert "human_review" in graph.nodes
    assert "log_result" in graph.nodes


# ── Task 5: E2E integration test ────────────────────────────────────

def test_run_billing_graph_flags_human_review_on_empty_entries():
    """If extraction returns no entries, needs_human_review must be True."""
    mock_audio = MagicMock()

    with patch("services.billing_graph._VECTOR_STORE", None), \
         patch("services.billing_graph._genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # classify_billable call → returns YES
        classify_resp = MagicMock()
        classify_resp.text = "YES"

        # extract_billing call → returns empty entries
        extract_resp = MagicMock()
        extract_resp.text = '{"entries": [], "confidence": 0.0}'
        extract_resp.parsed = None

        mock_client.models.generate_content.side_effect = [
            classify_resp,
            extract_resp,
        ]

        result = run_billing_graph(mock_audio, hourly_rate=2500)

    assert result["needs_human_review"] is True
    assert result["entries"] == []
    assert result["confidence"] == 0.0
    assert any("human_review" in line for line in result["audit_log"])


# -- Task 4: PAYE enrichment node (MCP integration) ---------------------------

def test_node_enrich_with_paye_skips_non_payroll_matters():
    """enrich_with_paye must be a no-op for non-payroll billing entries."""
    from services.billing_graph import node_enrich_with_paye
    state: BillingState = {
        "audio_ref": None,
        "hourly_rate": 2500,
        "policy_context": None,
        "raw_text": "client consultation contract review",
        "is_billable": True,
        "entries": [
            {
                "client_name": "Ndlovu Ltd",
                "matter_description": "contract review",
                "duration": "2 hours",
                "billable_amount": "R5000",
            }
        ],
        "confidence": 0.85,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    result = node_enrich_with_paye(state)
    # No payroll keywords -> audit_log should be empty or not mention paye
    log = result.get("audit_log", [])
    assert all("enrich_with_paye" not in line for line in log)


def test_node_enrich_with_paye_calculates_for_payroll_matters():
    """enrich_with_paye must log PAYE breakdown for payroll-related matters."""
    from services.billing_graph import node_enrich_with_paye
    state: BillingState = {
        "audio_ref": None,
        "hourly_rate": 2500,
        "policy_context": None,
        "raw_text": "paye calculation salary payroll",
        "is_billable": True,
        "entries": [
            {
                "client_name": "TechBridge",
                "matter_description": "payroll PAYE calculation for R600000 annual",
                "duration": "1 hour",
                "billable_amount": "R2500",
            }
        ],
        "confidence": 0.90,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    result = node_enrich_with_paye(state)
    log = result.get("audit_log", [])
    assert any("paye" in line.lower() for line in log)
    # Log should contain PAYE monthly figure
    assert any("paye/month" in line.lower() for line in log)
