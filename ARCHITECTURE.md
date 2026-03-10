# Architecture

## System Overview

LexFlow follows a monolithic deployment pattern with clear separation between the API layer and the client SPA. A single FastAPI process serves both the REST API and the compiled React frontend via static file mounting. The WhatsApp integration adds a second entry point via Meta Cloud API webhooks, enabling voice-to-billing from any phone.

```mermaid
graph LR
    A[React SPA] -->|fetch + Bearer token| B[FastAPI]
    W[WhatsApp] -->|Meta Cloud API webhook| B
    B -->|httpx REST| C[Supabase Auth]
    B -->|httpx REST| D[Supabase Postgres]
    B -->|genai SDK| E[Gemini API]
    B -->|httpx| F[Meta Graph API]
    C -->|JWT validation| B
    D -->|RLS enforcement| D
```

---

## Data Flow: Web — Voice Note to Billing Entry

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as FastAPI Backend
    participant G as Gemini API
    participant S as Supabase

    U->>F: POST /transcribe (audio + Bearer token)
    F->>S: Validate JWT via /auth/v1/user
    S-->>F: User identity (id, email)
    F->>S: GET profiles?id=eq.{user_id} (hourly_rate)
    S-->>F: hourly_rate (e.g. 2500)
    F->>G: Upload audio file
    G-->>F: file reference
    F->>G: Generate content (audio + billing prompt with rate)
    G-->>F: Structured JSON (client, matter, duration, amount)
    F->>G: Delete uploaded file (POPIA compliance)
    F-->>U: Return extraction for review (HITL)
    U->>U: User edits fields in review form
    U->>F: POST /billing (approved entry + Bearer token)
    F->>S: INSERT billing_entries (with user_id)
    S-->>F: 201 Created
    F-->>U: { status: "saved" }
```

---

## Data Flow: WhatsApp — Voice Note to Billing Entry

```mermaid
sequenceDiagram
    participant P as User (Phone)
    participant M as Meta Cloud API
    participant F as FastAPI Backend
    participant G as Gemini API
    participant S as Supabase

    P->>M: Send voice note via WhatsApp
    M->>F: POST /webhook (message payload)
    F->>S: Get/create whatsapp_users record
    S-->>F: User state + hourly_rate
    F-->>M: 200 OK (immediate)
    Note over F: Background task starts
    F->>M: GET media URL (download audio)
    M-->>F: Audio bytes
    F->>G: Upload audio + extraction prompt
    G-->>F: Structured billing data
    F->>G: Delete uploaded file (POPIA)
    F->>M: Send extraction summary to user
    M->>P: "Billing Entry — Client: X, Amount: R5,064"
    P->>M: Reply "YES"
    M->>F: POST /webhook (text: YES)
    F->>S: INSERT billing_entries
    F->>M: Send confirmation
    M->>P: "Saved to your ledger"
```

### WhatsApp State Machine

```mermaid
stateDiagram-v2
    [*] --> NEW: First message
    NEW --> AWAITING_RATE: Welcome sent
    AWAITING_RATE --> READY: Valid rate received
    READY --> AWAITING_APPROVAL: Voice note processed
    AWAITING_APPROVAL --> READY: YES / NO / EDIT
    READY --> READY: RATE / LINK / HELP commands
```

### Account Linking Flow

```mermaid
sequenceDiagram
    participant P as User (Phone)
    participant B as Browser
    participant F as FastAPI
    participant S as Supabase

    P->>F: Type "LINK" in WhatsApp
    F->>P: Link code + URL
    B->>F: Open /whatsapp/link/:code
    B->>F: Sign in or create account
    B->>F: POST /whatsapp/link {code}
    F->>S: Update whatsapp_users.user_id
    F->>S: Claim unlinked billing_entries
    F-->>B: { status: "linked" }
```

---

## Stack Decisions

### Why FastAPI over Django

FastAPI is async-first. The Gemini API call (audio upload + generation) takes 5-15 seconds. In Django, this blocks the WSGI worker. FastAPI handles it natively with `async/await`, keeping the server responsive during LLM latency. This is especially important for the WhatsApp webhook, which must return 200 within 5 seconds — the actual voice note processing runs as a `BackgroundTasks` coroutine.

### Why Supabase over Firebase

Row Level Security (RLS) is the key differentiator. Supabase enforces data isolation at the database level — a user physically cannot query another user's billing entries, even if the application code has a bug. Firebase Security Rules offer similar protection, but PostgreSQL's RLS is more natural for relational data and complex queries (joins, aggregations, CSV exports). Supabase also provides a standard REST API, making the backend stateless and easy to test.

### Why httpx over supabase-py

The official `supabase-py` package depends on `httpx` plus several C extensions (`gotrue`, `postgrest-py`, `realtime-py`). These fail to compile on Windows development machines and on Render's build environment without additional system dependencies. Using `httpx` directly against Supabase's REST API eliminates all C-extension build issues while providing the same functionality with fewer failure modes.

### Why WhatsApp over a Custom Mobile App

South African legal professionals already use WhatsApp daily for client communication. Building a native app would require download, install, and adoption — a significant barrier. WhatsApp integration means zero friction: send a voice note to a number, and billing is handled. The Meta Cloud API free tier (1,000 conversations/month) keeps costs at R0 for a portfolio project.

### Why Human-in-the-Loop (HITL) over Auto-Save

Legal billing demands accuracy. An AI extraction is a draft, not a fact. If the model misidentifies a client name or estimates duration incorrectly, automatically saving that to a FICA-compliant ledger creates a compliance risk. The HITL pattern — present, review, approve — is standard in enterprise AI workflows and demonstrates production-grade thinking. On WhatsApp, this translates to a simple YES/NO/EDIT reply.

### Why Sonner over Default Alerts

Sonner provides an `unstyled` mode that allows complete visual control. The toasts match the existing design system (frosted glass, tight typography, subtle accent borders) instead of looking like a generic library bolted on.

---

## Security Model

```
┌─────────────────────────────────────────────────┐
│                  Browser (SPA)                   │
│  supabaseClient.ts → Supabase Auth (anon key)   │
│  Stores JWT in memory (no localStorage)          │
└────────────────────┬────────────────────────────┘
                     │ Bearer token
┌────────────────────▼────────────────────────────┐
│               FastAPI Backend                    │
│  get_current_user() → validates JWT via          │
│  Supabase /auth/v1/user endpoint                 │
│  Extracts user.id for all DB operations          │
├──────────────────────────────────────────────────┤
│  WhatsApp webhook → service key operations       │
│  State tracked in whatsapp_users table           │
│  user_id linked only via authenticated flow      │
└────────────────────┬────────────────────────────┘
                     │ Service key (server-side only)
┌────────────────────▼────────────────────────────┐
│            Supabase PostgreSQL                   │
│  RLS Policy: billing_entries.user_id = auth.uid()│
│  WhatsApp entries: user_id NULL until linked     │
│  Service key bypasses RLS for webhook operations │
└─────────────────────────────────────────────────┘
```

**Key points:**
- The anon key is public (safe to expose in frontend). It only grants access through RLS.
- The service key is server-side only, used for admin operations, demo data seeding, and WhatsApp webhook operations.
- Audio files are never stored. They exist in memory during processing, are uploaded to Gemini for extraction, and immediately deleted via `files.delete()` in a `finally` block (POPIA/GDPR compliance).
- WhatsApp audio is downloaded to a temp file, processed, and deleted immediately — never persisted.

---

## Scope and Trade-offs

### What was explicitly deferred

| Feature | Reason for deferral |
|---------|-------------------|
| Multi-tenant admin panel | Focus on core AI extraction accuracy for individual users first |
| WebSocket real-time updates | Polling every 15s is sufficient for billing frequency; WebSockets add deployment complexity |
| Multi-currency support | App targets SA legal market; adding USD/GBP selection adds DB + prompt complexity for no current users |
| Background job queue | Audio processing takes ~10s; `BackgroundTasks` is sufficient at current scale |
| Offline/PWA support | Legal billing requires server-side AI processing; offline mode would be misleading |
| WhatsApp templates | Free-form messages work within the 24-hour conversation window; templates add Meta approval overhead |

### What would change at scale

- **Job queue** (Celery/Redis) for async audio processing if >10 concurrent users
- **Supabase Storage** for audio archival if client requests recording retention
- **Rate-based pricing tiers** via Stripe for multi-firm deployments
- **Audit trail table** for compliance logging of all data modifications
- **WhatsApp message templates** for outbound notifications beyond the 24h window

---

## Deployment

### Render (Production)

```yaml
# render.yaml
services:
  - type: web
    name: lexflow
    runtime: python
    buildCommand: npm --prefix frontend install && npm --prefix frontend run build && pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GOOGLE_API_KEY
      - key: SUPABASE_URL
      - key: SUPABASE_SERVICE_KEY
      - key: WHATSAPP_TOKEN
      - key: WHATSAPP_PHONE_ID
      - key: WEBHOOK_VERIFY_TOKEN
```

### Docker (Local/Self-hosted)

```bash
docker compose up --build
# → http://localhost:8000
```

The multi-stage Dockerfile builds the React frontend in a Node container, then copies the compiled `dist/` into a slim Python image. Final image is ~150MB.
