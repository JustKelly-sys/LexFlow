# LexFlow Evals

An evaluation harness for AI extraction from legal transaction documents,
built around South African deal mechanics. It measures, against hand-labeled
golden sets of clauses from public deal documents, three things:

| Metric | Question it answers |
|---|---|
| Clause-type accuracy | Does the model know what kind of clause it is reading? |
| Field-extraction accuracy | Are extracted values (fees, dates, governing law, consideration) exactly right? |
| Hallucination rate | When a clause does *not* contain a value, does the model correctly return null, or does it invent one? |

The hallucination metric is the point of this harness. Most extraction demos
only measure what the model gets right; this one measures what the model
makes up. Every clause is interrogated for seven fields, and most clauses
legitimately contain none of them, so inventing a value is caught and
counted.

## Golden sets

**South African** — `golden/aspi_renergen_2025_za.jsonl`: clauses from the
Firm Intention Letter Agreement for ASP Isotopes Inc.'s acquisition of
Renergen Limited (2025), a scheme of arrangement under **section 114(1)(d)
of the Companies Act 71 of 2008**. Publicly filed with the SEC (EDGAR
accession 0001477932-25-004002, exhibit 2.1). The clauses carry the real
machinery of an SA public-market deal:

- Takeover Regulation Panel compliance certificate (s121(b) Companies Act)
- FinSurv exchange-control approval (Currency and Exchanges Act, 1933)
- Competition Act 1998 clearances; JSE / A2X / ASX delisting conditions
- Scheme consideration ratio (0.09196 ASPI shares per Renergen share)
- Longstop date, MAC definition, SA governing law with Gauteng Division
  jurisdiction
- A deliberate trap: the consideration clause contains a **ZAR4,500,000 TRP
  escrow** (Takeover Regulations reg 111(4)) that is *not* a termination
  fee; a model that reports it as one is hallucinating a fee.

**United States** — `golden/aarons_iqventures_2024.jsonl`: clauses from the
Agreement and Plan of Merger between IQVentures Holdings and The Aaron's
Company (2024), SEC EDGAR accession 0001193125-24-162017. Included because
US/English-style paper is what most legal-AI platforms process daily; the
harness is jurisdiction-neutral by design.

Why EDGAR for both: it is the only large public corpus of *executed,
full-text* deal documents that is legally free to republish, and because
South African issuers and acquirers of SA companies file with the SEC, it
contains genuine SA-law agreements (the Renergen document above is one).

### Labeling rules (enforced on the model via the prompt)

- A field is non-null **only if the value is written in that clause**. A
  clause that references "the Merger Consideration" without stating the
  figure is labeled null — extracting the figure from elsewhere would be
  imported knowledge, exactly the failure mode this harness exists to catch.
- `governing_law_jurisdiction` counts only a designation of governing law,
  not any mention of a place (filings, courts, regulators, addresses).
- Escrows, guarantees and confirmations are not termination fees.

Current set: 25 seed items (8 SA + 17 US). Target: 200 items across ~10
agreements, weighted toward SA schemes and sale agreements. Adding items
means appending to a JSONL with the same labeling rules; `run_evals.py`
picks up every `golden/*.jsonl` automatically.

## Running

```bash
GOOGLE_API_KEY=... python evals/run_evals.py            # full set
python evals/run_evals.py --limit 5 --model gemini-3.1-flash-lite
```

Outputs a markdown summary table and `evals/results.json` with per-item
gold/prediction pairs and a list of every miss and hallucination.

## Results

Latest committed run (2026-07-12, `gemini-3.1-flash-lite`, 25-item seed set,
8 SA + 17 US):

| Metric | Value |
|---|---|
| Clause-type accuracy | 96.0% (24/25) |
| Field-extraction accuracy | 100.0% (175/175 fields) |
| Hallucination rate | 0.0% (0 of 166 null fields asserted) |

All 8 South African items scored perfectly, including the TRP-escrow trap
(the model correctly declined to report the ZAR4,500,000 escrow as a
termination fee) and exact extraction of the 0.09196 consideration ratio,
the 2025-09-30 longstop date, and South Africa as governing law. The single
miss is a borderline US classification (treasury-share cancellation labeled
`merger_mechanics` vs gold `consideration`), documented in `results.json`.

Numbers quoted anywhere (CV, README, LinkedIn) must come from a committed
`results.json`, reproducible with the command above.

## Method notes

- Temperature 0, structured output via a Pydantic schema (the same
  discipline the LexFlow production pipeline uses).
- Retries with backoff on rate limits; no retries on wrong answers.
- Numeric tolerance 0.00005 (exact for share ratios and dollar/rand figures).
- Free-tier note: Gemini quotas are per-model per-day; `--sleep` paces
  requests under the RPM cap.
- All source material is public record (SEC filings), so the entire harness
  is reproducible by anyone.
