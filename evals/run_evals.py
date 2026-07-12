"""
LexFlow Evals — clause classification + grounded field extraction benchmark.

Measures, against hand-labeled golden sets of clauses from public deal
documents (a South African scheme-of-arrangement firm intention agreement
under the Companies Act 71 of 2008, and a US merger agreement from SEC
EDGAR), three things:

  1. clause-type classification accuracy
  2. field-extraction accuracy (exact match per field)
  3. hallucination rate: how often the model asserts a value for a field the
     clause does not contain (gold = null, prediction != null)

Usage:
    GOOGLE_API_KEY=... python evals/run_evals.py [--limit N] [--model MODEL]

Writes evals/results.json and prints a markdown summary table.
"""
import argparse
import json
import os
import sys
import time

from pydantic import BaseModel
from google import genai

BASE = os.path.dirname(os.path.abspath(__file__))
GOLDEN_DIR = os.path.join(BASE, "golden")

CLAUSE_TYPES = [
    "merger_mechanics", "consideration", "payment_mechanics", "appraisal_rights",
    "equity_award_treatment", "conditions_to_closing", "termination_rights",
    "termination_fee", "amendment_waiver", "notices", "governing_law",
    "specific_performance", "definitions", "indemnification",
    "non_solicitation", "breach_and_remedies", "confidentiality",
    "miscellaneous",
]

EXTRACTION_FIELDS = [
    "governing_law_jurisdiction",
    "termination_fee_amount",
    "termination_fee_currency",
    "per_share_cash_amount",
    "per_share_cash_currency",
    "share_exchange_ratio",
    "longstop_date",
]


class ClauseExtraction(BaseModel):
    clause_type: str
    governing_law_jurisdiction: str | None
    termination_fee_amount: float | None
    termination_fee_currency: str | None
    per_share_cash_amount: float | None
    per_share_cash_currency: str | None
    share_exchange_ratio: float | None
    longstop_date: str | None  # ISO date YYYY-MM-DD


PROMPT = f"""You are a legal document analyst. Read the following clause from a
transaction agreement (it may be a South African scheme of arrangement under
the Companies Act 71 of 2008, or a US merger agreement) and return
structured data.

Rules — these are strict:
- clause_type: exactly one of {CLAUSE_TYPES}.
- governing_law_jurisdiction: ONLY if this clause itself designates a
  governing law (e.g. "governed by the laws of X"). Report the jurisdiction
  name only: "South Africa", "Georgia", "Delaware". A clause merely
  mentioning a place (filings, courts, addresses, regulators) does NOT
  count. Otherwise null.
- termination_fee_amount / termination_fee_currency: ONLY if this clause
  states a termination or break fee. Escrow amounts, guarantees and other
  figures are NOT termination fees. Currency as ISO code (USD, ZAR).
  Otherwise null.
- per_share_cash_amount / per_share_cash_currency: ONLY if this clause
  states cash consideration per share. Otherwise null.
- share_exchange_ratio: ONLY if this clause states a share-for-share
  exchange or consideration ratio (shares received per target share).
  Otherwise null.
- longstop_date: ONLY if this clause states the longstop/outside date as a
  calendar date; format YYYY-MM-DD. Otherwise null.
- Never infer a value from general knowledge or from other parts of the
  agreement. If the value is not written in this clause, return null.

CLAUSE:
{{clause}}
"""


def evaluate(items: list[dict], model: str, sleep_s: float = 13.0) -> dict:
    """sleep_s paces requests under the free-tier RPM limit."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    rows = []
    for i, item in enumerate(items, 1):
        if i > 1:
            time.sleep(sleep_s)
        for attempt in range(4):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=PROMPT.format(clause=item["text"]),
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ClauseExtraction,
                        "temperature": 0,
                    },
                )
                pred = resp.parsed if resp.parsed else ClauseExtraction(**json.loads(resp.text))
                break
            except Exception as e:
                if attempt == 3:
                    raise
                wait = 45 * (attempt + 1) if "429" in str(e) else 10 * (attempt + 1)
                print(f"  retry {item['id']} in {wait}s ({str(e)[:80]})", file=sys.stderr)
                time.sleep(wait)
        rows.append({"id": item["id"], "gold": item["labels"], "pred": pred.model_dump()})
        print(f"[{i}/{len(items)}] {item['id']}: {pred.clause_type}", file=sys.stderr)
    return score(rows)


def _norm(v):
    return v.strip().lower() if isinstance(v, str) else v


def score(rows: list[dict]) -> dict:
    n = len(rows)
    type_correct = sum(r["pred"]["clause_type"] == r["gold"]["clause_type"] for r in rows)

    field_total = field_correct = 0
    null_total = hallucinated = 0
    misses = []
    for r in rows:
        for f in EXTRACTION_FIELDS:
            gold, pred = r["gold"][f], r["pred"][f]
            field_total += 1
            match = (_norm(gold) == _norm(pred)) or (
                isinstance(gold, (int, float)) and isinstance(pred, (int, float))
                and abs(float(gold) - float(pred)) < 0.00005
            )
            field_correct += match
            if gold is None:
                null_total += 1
                if pred is not None:
                    hallucinated += 1
                    misses.append(f"HALLUCINATION {r['id']}.{f}: asserted {pred!r}, clause contains no value")
            elif not match:
                misses.append(f"MISS {r['id']}.{f}: expected {gold!r}, got {pred!r}")
        if r["pred"]["clause_type"] != r["gold"]["clause_type"]:
            misses.append(f"TYPE {r['id']}: expected {r['gold']['clause_type']}, got {r['pred']['clause_type']}")

    return {
        "items": n,
        "clause_type_accuracy": round(type_correct / n, 4),
        "field_accuracy": round(field_correct / field_total, 4),
        "hallucination_rate": round(hallucinated / null_total, 4) if null_total else None,
        "null_fields_tested": null_total,
        "misses": misses,
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=13.0,
                    help="seconds between requests (free tier RPM cap)")
    args = ap.parse_args()

    items = []
    for fn in sorted(os.listdir(GOLDEN_DIR)):
        if fn.endswith(".jsonl"):
            with open(os.path.join(GOLDEN_DIR, fn), encoding="utf-8") as f:
                items += [json.loads(l) for l in f if l.strip()]
    if args.limit:
        items = items[: args.limit]
    print(f"Evaluating {len(items)} golden items against {args.model}", file=sys.stderr)

    results = evaluate(items, args.model, args.sleep)
    results["model"] = args.model

    out = os.path.join(BASE, "results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n## Eval results — {args.model}\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Golden items | {results['items']} |")
    print(f"| Clause-type accuracy | {results['clause_type_accuracy']:.1%} |")
    print(f"| Field-extraction accuracy | {results['field_accuracy']:.1%} |")
    print(f"| Hallucination rate ({results['null_fields_tested']} null fields) | {results['hallucination_rate']:.1%} |")
    if results["misses"]:
        print("\nMisses:")
        for m in results["misses"]:
            print(f"- {m}")
    else:
        print("\nNo misses.")
    print(f"\nFull per-item output: {out}")


if __name__ == "__main__":
    main()
