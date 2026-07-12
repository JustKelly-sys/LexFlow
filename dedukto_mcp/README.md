# Dedukto MCP Server

**South African payroll tax engine exposed as Model Context Protocol (MCP) tools.**

Part of the [LexFlow AI Ops Suite](https://github.com/JustKelly-sys/LexFlow) — Layer 5 (System Integration).

---

## What This Is

Dedukto exposes SARS 2024/25 payroll calculations as MCP tools that any AI agent can call — Claude Desktop, a LangGraph agent, or any MCP-compatible client. The logic lives in one place; agents call it as a tool without reimplementing the tax logic.

---

## Tools

| Tool | Input | Output |
|---|---|---|
| `calculate_paye` | annual gross, jurisdiction, age | Full PAYE/UIF/SDL breakdown + net pay |
| `calculate_net_pay` | monthly gross, jurisdiction, age | Monthly net take-home |
| `list_tax_brackets` | jurisdiction | All 7 SARS 2024/25 brackets + rebate |

---

## Quick Start

```bash
# Run as standalone MCP server
python -m dedukto_mcp.server

# Or use directly as a Python library
python -c "from dedukto_mcp.tax_engine import calculate_paye_za; print(calculate_paye_za(600_000))"
```

---

## Example

```python
from dedukto_mcp.tax_engine import calculate_paye_za

result = calculate_paye_za(annual_gross=600_000)
print(f"PAYE/month:  R{result.paye_monthly:,.2f}")    # R11,136.42
print(f"UIF/month:   R{result.uif_monthly:,.2f}")     # R177.12
print(f"Net/month:   R{result.net_monthly:,.2f}")      # R38,686.46
print(f"Effective %: {result.effective_rate_pct}%")     # 22.27%
print(f"Marginal %:  {result.marginal_rate_pct}%")     # 31.0%
```

### MCP Tool Call (via server)

```json
{
  "tool": "calculate_paye",
  "arguments": {
    "gross_income": 600000,
    "jurisdiction": "ZA",
    "age": 30
  }
}
```

**Response:**
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

---

## Tax Engine Details

### SARS 2024/25 Brackets

| Bracket | Rate |
|---|---|
| R0 – R237,100 | 18% |
| R237,101 – R370,500 | 26% |
| R370,501 – R512,800 | 31% |
| R512,801 – R673,000 | 36% |
| R673,001 – R857,900 | 39% |
| R857,901 – R1,817,000 | 41% |
| R1,817,001+ | 45% |

### Rebates
- **Primary** (all ages): R17,235
- **Secondary** (65+): R9,444
- **Tertiary** (75+): R3,145

### Deductions
- **UIF**: 1% of monthly gross, capped at R177.12/month
- **SDL**: 1% of payroll (employer-paid, shown for reference)

---

## Input Validation

- `annual_gross < 0` → `ValueError`
- `age <= 0 or age > 120` → `ValueError`
- `monthly_gross < 0` → `ValueError`
- Unsupported jurisdiction → `ValueError` (only `ZA` currently supported)

---

## Testing

```bash
# Tax engine (13 tests)
python -m pytest tests/test_tax_engine.py -v

# MCP server tools (8 tests)
python -m pytest tests/test_mcp_server.py -v
```

Tests cover: all 7 brackets, rebate tiers, UIF ceiling, net pay formula, negative income guards, invalid age guards, tool registration, API structure, jurisdiction validation.

---

## Files

| File | Role |
|---|---|
| `dedukto_mcp/tax_engine.py` | Pure PAYE/UIF/SDL calculation (SARS 2024/25) |
| `dedukto_mcp/server.py` | FastMCP server — 3 tools |
| `tests/test_tax_engine.py` | 13 unit tests |
| `tests/test_mcp_server.py` | 8 integration tests |
| `docs/MCP_SERVER.md` | Full architecture writeup |

---

## Jurisdiction Roadmap

| Jurisdiction | Status |
|---|---|
| 🇿🇦 ZA (South Africa, SARS 2024/25) | ✅ Live |
| 🇬🇧 UK (HMRC 2024/25) | 📋 Planned |
| 🇺🇸 US (Federal 2024) | 📋 Planned |

---

## License

MIT

## Author

**Tshepiso Jafta** — [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
