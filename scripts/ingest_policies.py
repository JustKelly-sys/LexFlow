"""
One-off script: chunk and ingest billing policy documents into LanceDB.

Run from LexFlow/:
    python scripts/ingest_policies.py

Idempotent -- re-running upserts without duplicates.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.vector_store import VectorStore

POLICY_DIR = Path(__file__).parent.parent / "data" / "billing_policies"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
                current = current[-overlap:].strip() + "\n\n" + para
            else:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def ingest_all(store: VectorStore) -> int:
    md_files = list(POLICY_DIR.glob("*.md"))
    if not md_files:
        print(f"[ingest] No .md files found in {POLICY_DIR}")
        return 0
    total = 0
    for filepath in md_files:
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        source_name = filepath.name
        print(f"[ingest] {source_name} -- {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            doc_id = f"{source_name}__chunk_{i}"
            store.ingest(doc_id=doc_id, text=chunk, metadata={"source": source_name, "chunk_index": i})
            total += 1
    return total


if __name__ == "__main__":
    print("[ingest] Initialising VectorStore...")
    store = VectorStore()
    print(f"[ingest] Reading policies from: {POLICY_DIR}")
    count = ingest_all(store)
    print(f"[ingest] Done. {count} chunks stored in LanceDB.")

    print("\n[ingest] Smoke test -- querying: 'after hours weekend rate'")
    results = store.retrieve("after hours weekend rate", n_results=3)
    for r in results:
        print(f"  [{r['metadata']['source']}] distance={r['distance']:.4f}")
        print(f"  {r['text'][:120]}")
        print()

    print("[ingest] Smoke test -- querying: 'travel to client site'")
    results = store.retrieve("travel to client site", n_results=2)
    for r in results:
        print(f"  [{r['metadata']['source']}] distance={r['distance']:.4f}")
        print(f"  {r['text'][:120]}")
        print()
