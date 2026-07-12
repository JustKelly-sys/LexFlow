# LexFlow: AI Billing Intelligence for Legal Professionals

[![CI](https://github.com/TshepisoJafta/LexFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/TshepisoJafta/LexFlow/actions/workflows/ci.yml)

**Voice note in, reviewable billing entry out. Built for South African legal practice, with accuracy that is measured, not asserted.**

**[Live Demo](https://lexflow-rho.vercel.app)** · **[Published Evals](evals/)** · **[Architecture Docs](docs/)**

> **Recruiters:** click **"Try the demo"** on the login page, no signup required. The demo account seeds itself with sample data.

---

## What This Is

LexFlow converts voice dictations into structured billing entries for legal professionals. Dictate after a consultation, on the road, or over WhatsApp: LexFlow extracts client, matter, duration and billable amount with Google Gemini, scores its own confidence, and presents an editable review form for human verification before anything reaches the ledger. AI output is treated as a draft, never as a fact.

## Measured Accuracy

Extraction quality is benchmarked against a hand-labeled golden set of clauses from public deal documents, including a **South African scheme of arrangement under s114(1)(d) of the Companies Act 71 of 2008**. The benchmark's core metric is the hallucination rate: when a clause contains no value, does the model return null or invent one?

| Metric (latest committed run) | Value |
|---|---|
| Clause-type accuracy | 96.0% |
| Field-extraction accuracy | 100.0% |
| Hallucination rate | 0.0% (0 of 166 null fields) |

Methodology, golden sets and per-item results: [`evals/`](evals/). Reproducible end to end from public SEC filings.

---

## Architecture

| Layer | What It Does | Technology |
|---|---|---|
| 1. **Input Capture** | Voice notes via web or WhatsApp | FastAPI + Meta Cloud API |
| 2. **AI Processing** | Structured entity extraction with confidence scoring | Google Gemini, Pydantic structured output |
| 3. **RAG Retrieval** | Ground outputs in billing policy | LanceDB + Gemini embeddings (`gemini-embedding-001`) |
| 4. **Orchestration** | Stateful workflow with confidence routing | LangGraph (`BillingState` graph) |
| 5. **System Integration** | Payroll engine exposed as callable tools | Dedukto MCP Server (FastMCP) |

```
voice note -> [classify: billable?] -> [RAG: retrieve policy chunks]
           -> [Gemini: extract entries + confidence]
           -> confidence >= 0.7 -> log_result
           -> confidence <  0.7 -> human_review (flagged for HITL)
```

The RAG and LangGraph layers are optional by design: every import degrades gracefully to a direct Gemini extraction path, so the app runs identically on hosts that cannot carry the heavy dependencies. The production deployment on Vercel runs the direct path; the full pipeline runs anywhere the complete `requirements.txt` installs (Docker, Render, a VM) and is covered by the test suite either way.

---

## How It Works

### Web App
1. **Sign up**, set your hourly rate (ZAR)
2. **Dictate or upload**: record in-browser (with live waveform) or upload audio
3. **Review and approve**: extracted data appears in an editable form; low-confidence extractions are flagged
4. **Ledger**: approved records land in your personal billing ledger, exportable to CSV and PDF invoice

### WhatsApp
1. Send a voice note to the LexFlow WhatsApp number
2. Set your hourly rate on first use
3. Reply **YES** to save, **NO** to discard, **EDIT** to modify on web
4. Type **LINK** to connect WhatsApp to your web dashboard (entries made before linking are claimed retroactively)

---

## Security & Compliance

- **Supabase Auth** (JWT) with **Row Level Security**: users only ever see their own data
- **POPIA-conscious audio handling**: voice notes are processed and immediately deleted, from disk and from Gemini
- **Webhook signature verification** (HMAC-SHA256, constant-time comparison) that **fails closed in production**
- **Streaming upload cap** (25MB) enforced during the read, not just via Content-Length
- Input validation on every billing field; service-role database access confined to explicitly separate helpers

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Sonner, jsPDF |
| **Backend** | Python 3.12, FastAPI, Uvicorn, httpx |
| **AI** | Google Gemini API (`gemini-3.1-flash-lite` default), Pydantic structured output |
| **RAG** | LanceDB, Gemini embeddings (`gemini-embedding-001`) |
| **Orchestration** | LangGraph, `langchain-google-genai` |
| **MCP** | Dedukto MCP Server (`mcp>=1.0`, FastMCP pattern) |
| **Database / Auth** | Supabase (PostgreSQL, RLS, JWT auth) |
| **Messaging** | Meta Cloud API (WhatsApp Business) |
| **CI / Deployment** | GitHub Actions · Vercel (services: FastAPI + Vite) · Dockerfile for container hosts |

---

## Project Structure

```
LexFlow/
  main.py                # App assembly: CORS, routers, health, static serving
  config.py              # Environment configuration (single source of truth)
  auth.py                # JWT validation dependency
  routers/
    billing.py           # /transcribe, billing CRUD, CSV export, demo seeder
    profile.py           # Profile read/update
    whatsapp.py          # Meta webhook, account linking
  services/
    gemini.py            # Extraction schemas, prompt builder, retry logic
    billing_graph.py     # LangGraph 7-node billing pipeline
    vector_store.py      # LanceDB RAG layer
    whatsapp.py          # WhatsApp state machine and messaging
    supabase.py          # REST helpers (user-scoped vs service-role)
  evals/
    run_evals.py         # Extraction benchmark runner
    golden/              # Hand-labeled golden sets (SA + US deal documents)
    results.json         # Latest committed run
  dedukto_mcp/           # FastMCP server: SARS PAYE/UIF/SDL tools
  tests/                 # 65 tests across API, graph, RAG, MCP, tax engine
  migrations/            # SQL run in the Supabase SQL editor
  frontend/              # React 19 + Vite SPA
  Dockerfile             # Container build (frontend build + Python runtime)
  vercel.json            # Vercel services config (FastAPI + Vite)
```

---

## Getting Started

```bash
git clone https://github.com/TshepisoJafta/LexFlow.git
cd LexFlow

# Backend
python -m venv .venv
.venv\Scripts\activate            # Windows (source .venv/bin/activate on Unix)
pip install -r requirements.txt

# Frontend
cd frontend && npm ci && npm run build && cd ..

# Configure
cp .env.example .env               # then fill in your keys

# Run
python -m uvicorn main:app --port 8000
```

See [`.env.example`](.env.example) for the full variable list (Supabase, Gemini, WhatsApp, `APP_URL`/`APP_ENV`).

### Tests

```bash
python -m pytest tests/ -v         # 65 tests
```

### Evals

```bash
GOOGLE_API_KEY=... python evals/run_evals.py
```

### MCP server (standalone)

```bash
python -m dedukto_mcp.server
```

---

## API Endpoints

All endpoints except the frontend, `/health` and the webhook require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| POST | `/transcribe` | Extract billing data from audio |
| POST / GET | `/billing` | Save / list billing entries |
| GET | `/billing/csv` | Export as CSV |
| PATCH / DELETE | `/billing/{id}` | Update / delete an entry (ownership verified) |
| GET / PATCH | `/profile` | Read / update profile |
| GET / POST | `/webhook` | Meta verification / WhatsApp intake (HMAC-verified) |
| POST | `/whatsapp/link` | Link WhatsApp number to web account |

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Published evals over accuracy claims** | "Engineered so the model cannot invent details" is a claim; a golden set with a hallucination metric is evidence |
| **HITL over auto-save** | Legal billing demands accuracy; AI extraction is a draft, not a fact |
| **Confidence routing** | Entries below 0.7 confidence route to human review |
| **Graceful degradation** | RAG/LangGraph are optional imports; the core product runs on any free-tier host |
| **LangGraph over raw if/else** | Stateful graph: auditable, extensible, each node independently testable |
| **MCP over direct imports** | Any AI agent can call the payroll tools without embedding tax logic |
| **Supabase over Firebase** | Postgres + Row Level Security + built-in auth REST API |
| **WhatsApp over a custom app** | Legal professionals already live in WhatsApp; zero adoption friction |

---

## License

[MIT](LICENSE)

## Author

**Tshepiso Jafta** · [LinkedIn](https://www.linkedin.com/in/tshepisojafta/) · [GitHub](https://github.com/TshepisoJafta)
