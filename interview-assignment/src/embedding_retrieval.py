#!/usr/bin/env python3
"""Optional real-embedding retrieval layer.

This script upgrades the local TF-IDF retrieval prototype to real vector
embeddings when an OpenAI API key is available. It intentionally uses the
standard library HTTP client instead of requiring the OpenAI SDK, so the repo
still stays easy to run.

Run:
    OPENAI_API_KEY=... python3 src/embedding_retrieval.py \
      --meetings outputs/meeting_analysis.json \
      --output outputs

If OPENAI_API_KEY is not set, the script writes a status file explaining that
the embedding run was skipped. This keeps CI/tests deterministic while showing
the production path.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_QUERIES = [
    "Which calls show Detect reliability or outage risk?",
    "Where do customers mention renewal risk, pricing, or competitive evaluation?",
    "What product gaps should product managers prioritize?",
    "Which compliance or audit conversations need roadmap follow-up?",
    "Which identity and access issues are creating customer friction?",
]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def document_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key, ""))
        for key in ["title", "call_type", "primary_theme", "products", "topics", "summary", "example_quote"]
    )


def request_embeddings(
    texts: list[str],
    api_key: str,
    model: str,
    dimensions: int | None,
    retries: int = 3,
) -> list[list[float]]:
    payload: dict[str, Any] = {
        "model": model,
        "input": texts,
        "encoding_format": "float",
    }
    if dimensions:
        payload["dimensions"] = dimensions

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
                return [item["embedding"] for item in sorted(body["data"], key=lambda item: item["index"])]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Embedding request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Embedding request failed: {exc}") from exc

    raise RuntimeError("Embedding request failed after retries")


def embed_in_batches(
    texts: list[str],
    api_key: str,
    model: str,
    dimensions: int | None,
    batch_size: int,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        vectors.extend(request_embeddings(texts[start : start + batch_size], api_key, model, dimensions))
    return vectors


def search(
    rows: list[dict[str, Any]],
    doc_vectors: list[list[float]],
    query: str,
    query_vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    scored = sorted(
        ((cosine_similarity(query_vector, vector), row) for row, vector in zip(rows, doc_vectors)),
        key=lambda item: item[0],
        reverse=True,
    )
    return [
        {
            "query": query,
            "similarity": round(score, 4),
            "meeting_id": row["meeting_id"],
            "title": row["title"],
            "call_type": row["call_type"],
            "theme": row["primary_theme"],
            "products": row["products"],
            "risk_score": row["risk_score"],
            "evidence_quote": row["example_quote"],
        }
        for score, row in scored[:limit]
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meetings", type=Path, default=Path("outputs/meeting_analysis.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    status_path = args.output / "real_embedding_status.json"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        status_path.write_text(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "OPENAI_API_KEY is not set.",
                    "model": args.model,
                    "note": "Set OPENAI_API_KEY to generate real embedding retrieval outputs.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Skipped real embeddings; wrote {status_path}")
        return

    rows = json.loads(args.meetings.read_text(encoding="utf-8"))
    doc_texts = [document_text(row)[:7000] for row in rows]
    doc_vectors = embed_in_batches(doc_texts, api_key, args.model, args.dimensions, args.batch_size)
    query_vectors = embed_in_batches(DEFAULT_QUERIES, api_key, args.model, args.dimensions, args.batch_size)

    results: list[dict[str, Any]] = []
    for query, query_vector in zip(DEFAULT_QUERIES, query_vectors):
        results.extend(search(rows, doc_vectors, query, query_vector, args.limit))

    (args.output / "real_embedding_search_examples.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    status_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "model": args.model,
                "dimensions": args.dimensions,
                "documents_embedded": len(rows),
                "queries": len(DEFAULT_QUERIES),
                "output": "real_embedding_search_examples.json",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote real embedding search examples to {args.output / 'real_embedding_search_examples.json'}")


if __name__ == "__main__":
    main()
