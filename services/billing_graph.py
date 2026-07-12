"""
LexFlow Billing Pipeline — LangGraph Implementation

Replaces the linear _extract_billing() call with a stateful graph.

Graph flow:
  ingest_audio
      |
  classify_billable  (is this voice note about billable work?)
      |
  retrieve_context   (pull relevant policy chunks from LanceDB)
      |
  extract_billing    (Gemini structured output -> entries + confidence)
      |
  route_by_confidence --low confidence--> human_review (terminal)
      | high confidence
  log_result (terminal)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


# ==============================================================================
# State schema
# ==============================================================================

class BillingState(TypedDict):
    """Shared state passed between every graph node."""
    audio_ref: Any                  # Gemini uploaded file object
    hourly_rate: int                # Attorney ZAR/hr rate
    policy_context: str | None      # RAG-retrieved policy text
    raw_text: str                   # Filename/hint used for RAG query
    is_billable: bool | None        # Result of classify step
    entries: list[dict]             # Extracted billing entries
    confidence: float               # Overall confidence (0.0-1.0)
    audit_log: list[str]            # Append-only decision log
    needs_human_review: bool        # True when confidence < CONFIDENCE_THRESHOLD
    paye_enrichment: dict | None    # Populated by enrich_with_paye node


from config import CONFIDENCE_THRESHOLD

# Single source of truth for the extraction schemas — services.gemini
from services.gemini import (
    BillingEntry as _BillingEntry,        # noqa: F401 (kept for callers/tests)
    TranscriptionResult as _TranscriptionResult,
)


# ==============================================================================
# Module-level singletons
# ==============================================================================

try:
    from services.vector_store import VectorStore as _VS
    _VECTOR_STORE: _VS | None = _VS()
except Exception:
    _VECTOR_STORE = None

try:
    from google import genai as _genai
except ImportError:
    _genai = None  # type: ignore

try:
    from dedukto_mcp.tax_engine import calculate_paye_za as _calculate_paye_za
except ImportError:
    _calculate_paye_za = None  # type: ignore

_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# ==============================================================================
# Nodes
# ==============================================================================

def node_ingest_audio(state: BillingState) -> BillingState:
    """Pass-through — audio_ref already set by the endpoint."""
    log = list(state["audit_log"])
    log.append("ingest_audio: received audio_ref")
    return {**state, "audit_log": log}


def node_classify_billable(state: BillingState) -> BillingState:
    """
    Classify whether audio is billable legal work.
    Uses gemini-2.0-flash (cheapest). Fails open (True) on any error.
    """
    log = list(state["audit_log"])
    is_billable = True
    try:
        client = _genai.Client(api_key=_API_KEY)
        prompt = (
            "You are a legal billing classifier. "
            "Given a voice note, answer YES if it describes billable legal work "
            "(consultations, research, drafting, court appearances, client calls), "
            "or NO if it is a personal note, admin reminder, or non-billable. "
            "Reply with exactly one word: YES or NO.\n\n"
            f"Voice note content hint: {state.get('raw_text', '')}"
        )
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[state["audio_ref"], prompt],
        )
        is_billable = resp.text.strip().upper().startswith("YES")
    except Exception as e:
        log.append(f"classify_billable: error ({e}), defaulting to billable=True")

    log.append(f"classify_billable: is_billable={is_billable}")
    return {**state, "is_billable": is_billable, "audit_log": log}


def node_retrieve_context(state: BillingState) -> BillingState:
    """Pull relevant billing policy chunks from LanceDB (RAG)."""
    log = list(state["audit_log"])
    policy_context: str | None = state.get("policy_context")

    if _VECTOR_STORE is None:
        log.append("retrieve_context: vector store unavailable, skipping")
        return {**state, "policy_context": None, "audit_log": log}

    try:
        query = state.get("raw_text") or "billing policy"
        chunks = _VECTOR_STORE.retrieve(query, n_results=3)
        if chunks:
            policy_context = "\n\n".join(c["text"] for c in chunks)
            log.append(f"retrieve_context: retrieved {len(chunks)} chunks")
        else:
            log.append("retrieve_context: no chunks returned")
    except Exception as e:
        log.append(f"retrieve_context: error ({e}), skipping")

    return {**state, "policy_context": policy_context, "audit_log": log}


def node_extract_billing(state: BillingState) -> BillingState:
    """Call Gemini with structured output to extract billing entries + confidence."""
    log = list(state["audit_log"])
    rate = state["hourly_rate"]
    policy_ctx = state.get("policy_context")

    policy_block = (
        f"\n\nRELEVANT BILLING POLICY CONTEXT:\n{policy_ctx}\n"
        if policy_ctx else ""
    )

    prompt = (
        "You are a legal billing assistant. Listen to this voice note from a "
        "lawyer describing work they did.\n\n"
        "IMPORTANT: The voice note may describe work for MULTIPLE clients or matters. "
        "If so, create a SEPARATE entry for each distinct client/matter.\n\n"
        "For each entry, extract:\n"
        "- client_name: The client or party name. Use 'Unspecified Client' if none.\n"
        "- matter_description: Concise summary of the legal work.\n"
        "- duration: Duration of LEGAL WORK. Look for 'spent 2 hours', 'took 45 minutes'. "
        "If unspecified, estimate. Format as '2 hours' or '45 minutes'.\n"
        f"- billable_amount: Calculate using rate R{rate}/hr. "
        f"2 hours = 'R{rate * 2}', 30 min = 'R{rate // 2}'.\n\n"
        "Also provide a 'confidence' score (0.0 to 1.0) — lower if audio is unclear, "
        "names are ambiguous, or durations are estimated.\n\n"
        f"{policy_block}"
        "Return valid JSON matching the schema. Every field must be non-empty."
    )

    entries: list[dict] = []
    confidence: float = 0.0

    try:
        client = _genai.Client(api_key=_API_KEY)
        response = client.models.generate_content(
            model=_MODEL,
            contents=[state["audio_ref"], prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": _TranscriptionResult,
            },
        )
        result: _TranscriptionResult = (
            response.parsed
            if response.parsed
            else _TranscriptionResult(**json.loads(response.text))
        )
        entries = [e.model_dump() for e in result.entries]
        confidence = result.confidence
        log.append(f"extract_billing: {len(entries)} entries, confidence={confidence:.2f}")
    except Exception as e:
        log.append(f"extract_billing: error ({e})")

    return {**state, "entries": entries, "confidence": confidence, "audit_log": log}


def node_route_by_confidence(state: BillingState) -> BillingState:
    """Tag needs_human_review. Actual routing happens in the edge function."""
    log = list(state["audit_log"])
    needs_review = state["confidence"] < CONFIDENCE_THRESHOLD or not state["entries"]
    log.append(
        f"route_by_confidence: confidence={state['confidence']:.2f}, "
        f"needs_human_review={needs_review}"
    )
    return {**state, "needs_human_review": needs_review, "audit_log": log}


def node_log_result(state: BillingState) -> BillingState:
    """Terminal node: high-confidence path. Appends summary to audit log."""
    log = list(state["audit_log"])
    log.append(
        f"log_result: pipeline complete. "
        f"{len(state['entries'])} entries approved. "
        f"confidence={state['confidence']:.2f}"
    )
    return {**state, "audit_log": log}


def node_human_review(state: BillingState) -> BillingState:
    """Terminal node: low-confidence path. Flags for HITL review."""
    log = list(state["audit_log"])
    log.append(
        f"human_review: flagged for manual review. "
        f"confidence={state['confidence']:.2f}"
    )
    return {**state, "audit_log": log}




# ==============================================================================
# Node 8: enrich_with_paye (optional, MCP pattern demo)
# ==============================================================================

_PAYROLL_KEYWORDS = {
    "paye", "uif", "payroll", "salary", "sdl", "tax",
    "net pay", "gross pay", "deduction", "remuneration",
}


def node_enrich_with_paye(state: BillingState) -> BillingState:
    """
    If any billing entry mentions payroll/tax keywords, call the Dedukto tax engine
    to compute the actual PAYE breakdown and append it to the audit log.

    This node is OPTIONAL and not wired into the main billing graph critical path.
    It is imported by callers who want to demonstrate the MCP tool-calling pattern.

    In production this would call the MCP server via the MCP client protocol.
    For local use it calls the tax engine directly (same logic, same result).
    """
    log = list(state["audit_log"])
    entries = state.get("entries", [])

    for entry in entries:
        description = entry.get("matter_description", "").lower()
        if any(kw in description for kw in _PAYROLL_KEYWORDS):
            matches = re.findall(r"r?\s?(\d[\d,]+)", description)
            if matches:
                gross_str = matches[0].replace(",", "")
                try:
                    gross = float(gross_str)
                    if _calculate_paye_za is None:
                        log.append("enrich_with_paye: tax engine unavailable")
                        break
                    result = _calculate_paye_za(annual_gross=gross)
                    log.append(
                        f"enrich_with_paye: {entry['client_name']} "
                        f"gross=R{gross:,.0f} | "
                        f"PAYE/month=R{result.paye_monthly:,.2f} | "
                        f"net/month=R{result.net_monthly:,.2f}"
                    )
                except Exception as exc:
                    log.append(f"enrich_with_paye: calculation failed ({exc})")
            else:
                log.append("enrich_with_paye: no gross income amount found in description")
            break  # Only enrich the first payroll entry per invocation

    return {**state, "audit_log": log}

# ==============================================================================
# Graph assembly
# ==============================================================================

def _billable_router(state: BillingState) -> str:
    """Skip to human_review if audio is not billable legal work."""
    if state.get("is_billable") is False:
        return "human_review"
    return "retrieve_context"


def _confidence_router(state: BillingState) -> str:
    """Route to human_review or log_result based on confidence threshold."""
    if state["needs_human_review"]:
        return "human_review"
    return "log_result"


def build_billing_graph():
    """Compile and return the LexFlow billing LangGraph."""
    builder = StateGraph(BillingState)

    builder.add_node("ingest_audio", node_ingest_audio)
    builder.add_node("classify_billable", node_classify_billable)
    builder.add_node("retrieve_context", node_retrieve_context)
    builder.add_node("extract_billing", node_extract_billing)
    builder.add_node("route_by_confidence", node_route_by_confidence)
    builder.add_node("log_result", node_log_result)
    builder.add_node("human_review", node_human_review)

    builder.set_entry_point("ingest_audio")
    builder.add_edge("ingest_audio", "classify_billable")

    builder.add_conditional_edges(
        "classify_billable",
        _billable_router,
        {"retrieve_context": "retrieve_context", "human_review": "human_review"},
    )

    builder.add_edge("retrieve_context", "extract_billing")
    builder.add_edge("extract_billing", "route_by_confidence")

    builder.add_conditional_edges(
        "route_by_confidence",
        _confidence_router,
        {"log_result": "log_result", "human_review": "human_review"},
    )

    builder.add_edge("log_result", END)
    builder.add_edge("human_review", END)

    return builder.compile()


# Module-level compiled graph — import once, reuse across requests
BILLING_GRAPH = build_billing_graph()


def run_billing_graph(
    audio_ref: Any,
    hourly_rate: int,
    raw_text: str = "",
    policy_context: str | None = None,
) -> dict:
    """
    Invoke the LangGraph billing pipeline synchronously.

    Returns: {entries, confidence, needs_human_review, audit_log}
    """
    initial_state: BillingState = {
        "audio_ref": audio_ref,
        "hourly_rate": hourly_rate,
        "policy_context": policy_context,
        "raw_text": raw_text,
        "is_billable": None,
        "entries": [],
        "confidence": 0.0,
        "audit_log": [],
        "needs_human_review": False,
        "paye_enrichment": None,
    }
    final_state = BILLING_GRAPH.invoke(initial_state)
    return {
        "entries": final_state["entries"],
        "confidence": final_state["confidence"],
        "needs_human_review": final_state["needs_human_review"],
        "audit_log": final_state["audit_log"],
    }


