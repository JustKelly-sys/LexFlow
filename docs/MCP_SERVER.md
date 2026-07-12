# Dedukto MCP Server

## What This Is

The Dedukto MCP Server exposes South Africa's SARS payroll tax engine as a
**Model Context Protocol** tool. Any MCP-compatible AI agent — Claude Desktop,
a LangGraph agent, or any future AI client — can invoke:

- `calculate_paye(gross_income, jurisdiction, age)` - full tax breakdown
- `calculate_net_pay(gross_monthly, jurisdiction, age)` - monthly net pay
- `list_tax_brackets(jurisdiction)` - tax table reference

## Why MCP?

**The problem MCP solves:** Payroll calculation logic is complex and jurisdiction-specific.
Without MCP, every AI agent that needs to answer "what's the net pay on R600,000?"
must either (a) hallucinate an answer, (b) call a hardcoded API, or (c) embed the
tax logic directly in its codebase.

**With MCP:** The logic lives in one place. Agents call it as a tool. This is the
same pattern that lets Claude Desktop call web search, file systems, and databases -
one interface, unlimited callers.

## Running the Server

```bash
python -m dedukto_mcp.server
# or
uv run dedukto_mcp/server.py
```

## Tool Reference

### `calculate_paye`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `gross_income` | float | required | Annual gross in local currency |
| `jurisdiction` | str | `"ZA"` | `"ZA"` = South Africa (SARS 2024/25) |
| `age` | int | `30` | Affects rebate tier |

**Example response (R600,000 annual gross):**
```json
{
  "jurisdiction": "ZA",
  "currency": "ZAR",
  "gross_annual": 600000,
  "gross_monthly": 50000.0,
  "paye_annual": 133637.0,
  "paye_monthly": 11136.42,
  "effective_rate_pct": 22.27,
  "marginal_rate_pct": 31.0,
  "rebate_applied": 17235.0,
  "uif_monthly": 177.12,
  "sdl_monthly_employer": 500.0,
  "net_annual": 464117.44,
  "net_monthly": 38676.45,
  "tax_year": "2024/25"
}
```

### `calculate_net_pay`

Convenience wrapper. Input: `gross_monthly`. Output: `{net_monthly, paye_monthly, uif_monthly}`.

### `list_tax_brackets`

Returns all 7 SARS 2024/25 tax brackets with the primary rebate (R17,235).

## The LangGraph Integration

The `node_enrich_with_paye` node in `services/billing_graph.py` demonstrates the
MCP tool-calling pattern within the LexFlow LangGraph pipeline:

```
billing audio --> [classify] --> [RAG] --> [extract] --> [route]
                                                              |
                                                 (if payroll matter)
                                                              |
                                                 node_enrich_with_paye
                                                 calls calculate_paye_za()
                                                 --> appends PAYE breakdown
                                                     to audit_log
```

When a billing entry contains payroll keywords (paye, uif, salary, payroll),
the node extracts the gross income from the description and appends a full
PAYE breakdown to the audit log automatically.

## Architecture Significance

> "I exposed a domain-specific calculation engine as a reusable MCP server.
> Any LangGraph agent -- LexFlow, a future KYC tool, or a client's own AI
> assistant -- can call `calculate_paye()` as a tool without reimplementing
> the SARS tax logic. Write once, connect anywhere."

This is **Layer 5** of the AI Workflow Automation stack: System Integration via MCP.

| Layer | What it is | LexFlow Implementation |
|---|---|---|
| 1. Input Capture | Voice notes, documents | WhatsApp + FastAPI upload |
| 2. AI Processing | LLM inference | Google Gemini (structured output) |
| 3. RAG Retrieval | Policy grounding | LanceDB + policy ingestion |
| 4. Orchestration | Stateful workflow | LangGraph BillingState graph |
| 5. System Integration | Tool calling | Dedukto MCP Server |

## Files

| File | Role |
|---|---|
| `dedukto_mcp/tax_engine.py` | Pure PAYE/UIF/SDL calculation (SARS 2024/25) |
| `dedukto_mcp/server.py` | FastMCP server — exposes 3 tools |
| `tests/test_tax_engine.py` | 9 unit tests for calculation correctness |
| `tests/test_mcp_server.py` | 8 integration tests for tool registration |
| `services/billing_graph.py` | `node_enrich_with_paye` demonstrates tool-calling |

## Jurisdiction Roadmap

| Jurisdiction | Status |
|---|---|
| ZA (South Africa, SARS 2024/25) | Live |
| UK (HMRC 2024/25) | Planned |
| US (Federal 2024) | Planned |
