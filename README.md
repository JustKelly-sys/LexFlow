# LexFlow — AI Ops Suite for Legal Billing

**Voice-to-billing intelligence with RAG, LangGraph orchestration, and MCP tool integration.**

**[Live Demo](https://lexflow-dwa0.onrender.com)** · **[Architecture Docs](docs/)**

---

## What This Is

LexFlow converts voice dictations into structured billing entries for South African legal professionals. Dictate via WhatsApp or the web app — LexFlow transcribes with Google Gemini, retrieves relevant billing policy via RAG, orchestrates extraction through a stateful LangGraph pipeline, and presents an editable review form for human verification before committing to your personal ledger.

> **Recruiters:** Click **"Try Demo"** on the login page — no signup required.

---

## Architecture — 5-Layer AI Stack

| Layer | What It Does | Technology |
|---|---|---|
| 1. **Input Capture** | Voice notes via web or WhatsApp | FastAPI + Meta Cloud API |
| 2. **AI Processing** | Structured entity extraction | Google Gemini (`gemini-2.0-flash`) |
| 3. **RAG Retrieval** | Ground outputs in billing policy | LanceDB + sentence-transformers |
| 4. **Orchestration** | Stateful workflow with confidence routing | LangGraph (`BillingState` graph) |
| 5. **System Integration** | Expose payroll engine as callable tools | Dedukto MCP Server (FastMCP) |

```
voice note → [classify: billable?] → [RAG: retrieve policy chunks]
           → [Gemini: extract entries + confidence]
           → confidence >= 0.7 → log_result ✅
           → confidence <  0.7 → human_review ⚠️ (flagged in WhatsApp)
```

---

## How It Works

### Web App
1. **Sign Up** — Create an account with your email and set your custom hourly rate (ZAR)
2. **Dictate or Upload** — Record a voice note in-browser or upload an audio file
3. **Review & Approve** — Extracted billing data appears in an editable form for human verification
4. **Ledger Entry** — Approved records are saved to your personal billing ledger

### WhatsApp
1. **Send a message** — Text or voice note to the LexFlow WhatsApp number
2. **Set your rate** — Reply with your hourly billing rate on first use
3. **Send a voice note** — Describe your billable work naturally
4. **Approve or reject** — Reply YES, NO, or EDIT to the extracted entry
5. **Link your account** — Type LINK to connect WhatsApp to your web dashboard

---

## Features

### Core Pipeline
- **Voice Dictation** — Record directly from the browser with real-time waveform visualization
- **Audio Upload** — Supports MP3, WAV, M4A, WebM, FLAC, AAC, OGG (25MB max)
- **Gemini Extraction** — Structured entity extraction with Pydantic validation
- **RAG Policy Grounding** — Billing outputs are grounded against ingested policy documents via LanceDB
- **LangGraph Orchestration** — 7-node stateful graph with conditional confidence routing
- **Dedukto MCP Integration** — Payroll-related matters auto-enrich with PAYE/UIF/SDL breakdown

### WhatsApp Integration
- **Voice Notes** — Send voice note → Gemini extracts billing data automatically
- **Conversational Approval** — Reply YES to save, NO to discard, EDIT to modify on web
- **Account Linking** — Type LINK to connect WhatsApp to your web dashboard
- **State Machine** — Clean conversation flow (NEW → AWAITING_RATE → READY → AWAITING_APPROVAL)
- **POPIA Compliance** — Voice notes downloaded, processed, and immediately deleted

### Human-in-the-Loop (HITL)
- **Editable Review Form** — Verify and correct all fields before saving
- **Confidence Scoring** — Visual confidence bar; low-confidence entries flagged for review
- **Batch Approval** — Approve all entries at once with failure tracking

### Authentication & Security
- **Supabase Auth** — Email + password with JWT session management
- **Row Level Security** — Users only see their own billing data
- **HMAC Webhook Verification** — Meta payload verified with constant-time comparison
- **Upload Size Guard** — 25MB hard limit before file read
- **Input Validation** — All billing fields validated for length (2000 char max) and content
- **POPIA Compliance** — Audio files scrubbed from Gemini immediately after extraction

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS v4, Sonner, jsPDF |
| **Backend** | Python, FastAPI, Uvicorn, httpx |
| **AI** | Google Gemini API (`gemini-2.0-flash`), Pydantic structured output |
| **RAG** | LanceDB, sentence-transformers (`all-MiniLM-L6-v2`) |
| **Orchestration** | LangGraph (`langgraph>=1.1.6`), `langchain-google-genai` |
| **MCP** | Dedukto MCP Server (`mcp>=1.0`, FastMCP pattern) |
| **Database** | Supabase (PostgreSQL + Row Level Security) |
| **Auth** | Supabase Auth (email + password, JWT) |
| **Messaging** | Meta Cloud API (WhatsApp Business) |
| **Deployment** | Render (auto-deploy from GitHub) |

---

## Project Structure

```
LexFlow/
  main.py                     # FastAPI backend + Gemini + Supabase + WhatsApp
  config.py                   # Environment configuration (single source of truth)
  auth.py                     # JWT validation dependency
  requirements.txt            # Python dependencies
  render.yaml                 # Render deployment config

  services/
    billing_graph.py           # LangGraph 7-node billing pipeline
    vector_store.py            # LanceDB RAG layer
    supabase.py                # Supabase REST helpers

  dedukto_mcp/
    server.py                  # FastMCP server — 3 payroll tools
    tax_engine.py              # SARS 2024/25 PAYE/UIF/SDL pure functions
    README.md                  # Dedukto quick-start

  tests/
    test_lexflow.py            # 26 tests: schemas, CRUD, CORS, validation
    test_billing_graph.py      # 9 tests: LangGraph nodes, routing, PAYE enrichment
    test_tax_engine.py         # 13 tests: bracket logic, rebates, input guards
    test_mcp_server.py         # 8 tests: tool registration, API structure
    test_vector_store.py       # 7 tests: ingest, retrieve, prompt building

  docs/
    LANGGRAPH_ARCHITECTURE.md  # Graph flow, cost model, state schema
    MCP_SERVER.md              # 5-layer architecture writeup

  frontend/                    # React 19 + Vite SPA
    src/
      pages/                   # Dashboard, Dictation, Review, Ledger, etc.
      components/lexflow/      # AuthPage, Navbar, BillingLedger, Waveform, etc.
```

---

## Getting Started

```bash
git clone https://github.com/JustKelly-sys/LexFlow.git
cd LexFlow

# Backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..

# Environment (.env)
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
WHATSAPP_TOKEN=your_meta_cloud_api_token
WHATSAPP_PHONE_ID=your_whatsapp_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_custom_webhook_token
WHATSAPP_APP_SECRET=your_meta_app_secret

# Run
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### MCP Server (standalone)
```bash
python -m dedukto_mcp.server
```

---

## Testing

```bash
# Run full suite (65 tests)
python -m pytest tests/ -v

# Individual modules
python -m pytest tests/test_lexflow.py -v        # Core API (26 tests)
python -m pytest tests/test_billing_graph.py -v   # LangGraph pipeline (9 tests)
python -m pytest tests/test_tax_engine.py -v      # Tax engine (13 tests)
python -m pytest tests/test_mcp_server.py -v      # MCP tools (8 tests)
python -m pytest tests/test_vector_store.py -v    # RAG layer (7 tests)
```

---

## API Endpoints

All endpoints except frontend and webhook require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | React SPA (dashboard) |
| POST | `/transcribe` | Extract billing data from audio (25MB max) |
| POST | `/billing` | Save a user-approved billing entry |
| GET | `/billing` | Get authenticated user's billing entries |
| GET | `/billing/csv` | Download billing data as CSV |
| DELETE | `/billing/{id}` | Delete a billing entry (ownership verified) |
| PATCH | `/billing/{id}` | Update a billing entry (ownership verified) |
| GET | `/profile` | Get user profile |
| PATCH | `/profile` | Update profile (name, firm, rate) |
| GET | `/webhook` | Meta webhook verification |
| POST | `/webhook` | Receive WhatsApp messages (HMAC-verified) |
| POST | `/whatsapp/link` | Link WhatsApp number to web account |

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over raw if/else** | Stateful graph = auditable, extensible, each node independently testable |
| **RAG over hardcoded prompts** | Policy documents change; semantic retrieval adapts without code changes |
| **MCP over direct imports** | Any AI agent can call `calculate_paye()` without embedding tax logic |
| **FastAPI over Django** | Async-first — handles Gemini API latency without blocking |
| **Supabase over Firebase** | Postgres + Row Level Security + built-in auth REST API |
| **HITL over auto-save** | Legal billing demands accuracy — AI extraction is a draft, not a fact |
| **WhatsApp over custom app** | Legal professionals already use WhatsApp daily; zero adoption friction |
| **Confidence routing** | Entries below 0.7 confidence → human review; above → auto-approve path |

---

## License

MIT

## Author

**Tshepiso Jafta** — [LinkedIn](https://www.linkedin.com/in/tshepisojafta/)
