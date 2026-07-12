"""
LanceDB vector store service for LexFlow billing policy retrieval.

Responsibilities:
- Embed text using Gemini gemini-embedding-001 (via google-genai SDK)
- Persist embeddings in a local LanceDB table
- Retrieve semantically relevant chunks using cosine similarity

Usage:
    store = VectorStore()
    store.ingest(doc_id="policy_001", text="...", metadata={"source": "file.md"})
    results = store.retrieve("after hours consultation", n_results=3)
"""
import os
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import lancedb
from google import genai


# ── Constants ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072               # gemini-embedding-001 output dimension
# Anchor to the repo, not the process CWD — a server started from another
# directory would otherwise silently create a second, empty index.
DEFAULT_PERSIST_DIR = str(Path(__file__).resolve().parent.parent / "lance_db")
DEFAULT_TABLE = "lexflow_billing_policies"


class VectorStore:
    """Thin wrapper around LanceDB for LexFlow billing policy RAG."""

    def __init__(
        self,
        persist_dir: str = DEFAULT_PERSIST_DIR,
        table_name: str = DEFAULT_TABLE,
    ) -> None:
        self._db = lancedb.connect(persist_dir)
        self._table_name = table_name
        self._table = self._get_or_create_table()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable is required for embeddings.")
        self._genai = genai.Client(api_key=api_key)

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest(self, doc_id: str, text: str, metadata: dict[str, Any]) -> None:
        """Embed text and upsert into the table by doc_id."""
        embedding = self._embed(text)
        source = metadata.get("source", "")
        chunk_index = int(metadata.get("chunk_index", 0))

        row = {
            "id": doc_id,
            "vector": embedding,
            "text": text,
            "source": source,
            "chunk_index": chunk_index,
        }

        # Delete existing row with same id, then add new one (upsert pattern)
        try:
            self._table.delete(f"id = '{doc_id}'")
        except Exception:
            pass  # Table may be empty or id may not exist
        self._table.add([row])

    def retrieve(self, query: str, n_results: int = 3) -> list[dict[str, Any]]:
        """Retrieve the n most semantically relevant chunks for a query.

        Returns a list of dicts: [{"text": str, "metadata": dict, "distance": float}]
        Returns [] if the table is empty.
        """
        count = self._table.count_rows()
        if count == 0:
            return []

        safe_n = min(n_results, count)
        query_embedding = self._embed(query)

        results = (
            self._table.search(query_embedding)
            .limit(safe_n)
            .select(["id", "text", "source", "chunk_index", "_distance"])
            .to_list()
        )

        chunks = []
        for row in results:
            chunks.append({
                "text": row["text"],
                "metadata": {"source": row["source"], "chunk_index": row["chunk_index"]},
                "distance": row.get("_distance", 0.0),
            })
        return chunks

    def count(self) -> int:
        """Return the number of stored chunks."""
        return self._table.count_rows()

    # ── Private ───────────────────────────────────────────────────────────────

    def _get_or_create_table(self):
        """Return an existing table or create one with the correct schema."""
        raw = self._db.list_tables()
        # LanceDB 0.30+ returns ListTablesResponse; older returns a plain list
        existing = raw.tables if hasattr(raw, "tables") else list(raw)
        if self._table_name in existing:
            return self._db.open_table(self._table_name)
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
            pa.field("text", pa.string()),
            pa.field("source", pa.string()),
            pa.field("chunk_index", pa.int32()),
        ])
        return self._db.create_table(self._table_name, schema=schema)

    def _embed(self, text: str) -> list[float]:
        """Call Gemini text-embedding-004 and return the embedding vector."""
        response = self._genai.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return response.embeddings[0].values
