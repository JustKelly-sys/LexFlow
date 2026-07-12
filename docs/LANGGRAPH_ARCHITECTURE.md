# LexFlow LangGraph Architecture

## Graph Overview

```
ingest_audio
    |
classify_billable ── not billable ──> human_review --> END
    | billable
retrieve_context   (RAG: LanceDB policy chunks)
    |
extract_billing    (Gemini structured output)
    |
route_by_confidence
    |-- confidence >= 0.7 --> log_result --> END
    |-- confidence <  0.7 --> human_review --> END
```

## State Schema (BillingState)

| Field | Type | Description |
|---|---|---|
| `audio_ref` | Any | Gemini Files API uploaded file object |
| `hourly_rate` | int | Attorney ZAR/hr rate |
| `policy_context` | str \| None | RAG-retrieved billing policy text |
| `raw_text` | str | Filename/hint used for RAG query |
| `is_billable` | bool \| None | Classifier node output |
| `entries` | list[dict] | Extracted billing entries |
| `confidence` | float | Extraction confidence (0.0-1.0) |
| `audit_log` | list[str] | Append-only decision log |
| `needs_human_review` | bool | True if confidence < 0.7 |
| `paye_enrichment` | dict \| None | Populated by Week 4 MCP node |

## Confidence Threshold

`CONFIDENCE_THRESHOLD = 0.7`

Low-confidence extractions are flagged with `needs_human_review: True`.
The endpoint returns the entries but the frontend/WhatsApp handler surfaces a review warning.

## Cost Model

| Node | Model | Reason |
|---|---|---|
| `classify_billable` | `gemini-2.0-flash` | Binary decision — cheapest model |
| `retrieve_context` | No LLM (vector search) | Near-zero cost |
| `extract_billing` | `gemini-2.0-flash` (default) | Configurable via GEMINI_MODEL env |

## Key Files

| File | Role |
|---|---|
| `services/billing_graph.py` | Graph definition, all nodes, `run_billing_graph()` |
| `services/vector_store.py` | LanceDB RAG layer (Week 2) |
| `tests/test_billing_graph.py` | Unit + integration tests |
| `scripts/ingest_policies.py` | Policy ingestion script (Week 1) |
