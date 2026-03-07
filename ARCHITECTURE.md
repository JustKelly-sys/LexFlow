# LexFlow Architecture

## System Overview

```
Voice Note (.mp3/.wav/.m4a)
        |
        v
  [FastAPI Server]
        |
        v
  [Gemini File API] --> Upload audio
        |
        v
  [Gemini Generate] --> Structured JSON extraction
        |                (client, matter, duration, amount)
        v
  [CSV Storage] --> Persistent billing ledger
        |
        v
  [Dashboard UI] --> Real-time display with auto-refresh
```

## Key Design Decisions

### Why FastAPI?
FastAPI provides automatic OpenAPI docs, async support, and native Pydantic integration for request/response validation. This is critical for a billing tool where data accuracy matters.

### Why CSV over a Database?
For the initial version, CSV provides portability. Law firms can open billing exports directly in Excel without needing database tooling. A PostgreSQL migration is planned for v3.

### Why Embedded HTML?
The dashboard is served as a single HTML string from the FastAPI app. This eliminates the need for a separate frontend build step and makes deployment as simple as running one Python file.

### Rate Limiting Strategy
Gemini API uses token-based rate limits. LexFlow implements exponential backoff (5s base, 3 retries) to handle 429 responses gracefully without losing the attorney's voice note data.

### ZAR Billing
Default billing rate is R2,500/hour, reflecting standard South African attorney rates. This is configurable in the prompt template.
