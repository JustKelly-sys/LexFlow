# LexFlow Evals

An evaluation harness for AI extraction from legal documents. It measures,
against a hand-labeled golden set of clauses taken from public SEC EDGAR
merger agreements, three things:

| Metric | Question it answers |
|---|---|
| Clause-type accuracy | Does the model know what kind of clause it is reading? |
| Field-extraction accuracy | Are extracted values (fees, dates, governing law, consideration) exactly right? |
| Hallucination rate | When a clause does *not* contain a value, does the model correctly return null, or does it invent one? |

The hallucination metric is the point of this harness. Most extraction demos
only measure what the model gets right; this one measures what the model
makes up. Fields in the golden set are deliberately null-heavy: every clause
is asked for all four extraction fields, and most clauses legitimately
contain none of them.

## Golden set

`golden/aarons_iqventures_2024.jsonl` — clauses from the Agreement and Plan
of Merger between IQVentures Holdings, LLC and The Aaron's Company, Inc.
(June 2024), a public record filed with the SEC (EDGAR accession
0001193125-24-162017, exhibit 2.1). Each item carries the verbatim clause
text and hand-checked labels:

```json
{
  "id": "company_term_fee",
  "source": "…EDGAR URL…",
  "text": "…verbatim clause…",
  "labels": {
    "clause_type": "termination_fee",
    "governing_law_state": null,
    "termination_fee_usd": 12500000,
    "per_share_consideration_usd": null,
    "outside_date": null
  }
}
```

Labeling rules (also enforced on the model via the prompt):

- A field is non-null **only if the value is written in that clause**. A
  clause that references "the Merger Consideration" without stating the
  dollar figure is labeled null — extracting the figure from elsewhere in
  the agreement would be imported knowledge, which is exactly the failure
  mode this harness exists to catch.
- `governing_law_state` counts only a designation of governing law, not any
  mention of a state (filing offices, courts, addresses do not count).

Current set: 17 seed items, one agreement. Target: 200 items across ~10
agreements (EDGAR has an effectively unlimited supply). Adding items means
appending to the JSONL with the same labeling rules; `run_evals.py` picks up
every `golden/*.jsonl` automatically.

## Running

```bash
GOOGLE_API_KEY=... python evals/run_evals.py            # full set
python evals/run_evals.py --limit 5 --model gemini-2.0-flash
```

Outputs a markdown summary table and `evals/results.json` with per-item
gold/prediction pairs and a list of every miss and hallucination.

## Results

Latest committed run (2026-07-12, `gemini-3.1-flash-lite`, 17-item seed set):

| Metric | Value |
|---|---|
| Clause-type accuracy | 94.1% (16/17) |
| Field-extraction accuracy | 100.0% (68/68 fields) |
| Hallucination rate | 0.0% (0 of 64 null fields asserted) |

The single miss: a treasury-share cancellation clause classified as
`merger_mechanics` instead of `consideration`, a borderline call that the
taxonomy arguably permits. Full per-item gold/prediction pairs are in
`results.json`.

Numbers quoted anywhere (CV, README, LinkedIn) must come from a committed
`results.json`, reproducible with the command above. Free-tier note:
Gemini free quotas are per-model per-day (20/day for 2.5-flash; the lite
models are more generous); `--sleep` paces requests under the RPM cap.

## Method notes

- Temperature 0, structured output via a Pydantic schema (the same
  discipline the LexFlow production pipeline uses).
- Retries with backoff on rate limits; no retries on wrong answers.
- Numeric comparison tolerance is 0.005 (cents-exact for dollar figures).
- The golden set is public-domain source material (SEC filings), so the
  entire harness is reproducible by anyone.
