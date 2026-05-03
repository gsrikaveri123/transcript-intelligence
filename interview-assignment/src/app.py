#!/usr/bin/env python3
"""Optional FastAPI app for interactive transcript intelligence review.

Install optional dependencies:
    python3 -m pip install -r requirements-optional.txt

Run:
    uvicorn src.app:app --reload --app-dir .
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, Query
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without optional deps
    raise ModuleNotFoundError(
        "FastAPI is optional. Install it with: python3 -m pip install -r requirements-optional.txt"
    ) from exc


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def read_json(name: str, default: Any) -> Any:
    path = OUTPUT_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


app = FastAPI(
    title="Transcript Intelligence API",
    version="1.0.0",
    description="Review API for transcript themes, sentiment, risk routing, retrieval examples, and evaluation metrics.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/summary")
def summary() -> dict[str, Any]:
    return {
        "summary_metrics": read_json("summary_metrics.json", {}),
        "evaluation_metrics": read_json("evaluation_metrics.json", {}),
        "gold_label_evaluation": read_json("gold_label_evaluation.json", {}),
        "real_embedding_status": read_json("real_embedding_status.json", {"status": "not_run"}),
    }


@app.get("/meetings")
def meetings(
    theme: str | None = None,
    call_type: str | None = None,
    min_risk: int = Query(default=0, ge=0, le=10),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[dict[str, Any]]:
    rows = read_json("meeting_analysis.json", [])
    filtered = [
        row
        for row in rows
        if (theme is None or row["primary_theme"] == theme)
        and (call_type is None or row["call_type"] == call_type)
        and int(row["risk_score"]) >= min_risk
    ]
    return filtered[:limit]


@app.get("/search-examples")
def search_examples(real_embeddings: bool = False) -> list[dict[str, Any]]:
    if real_embeddings:
        return read_json("real_embedding_search_examples.json", [])
    return read_json("semantic_search_examples.json", [])


@app.get("/review-queue")
def review_queue() -> list[dict[str, Any]]:
    return read_json("evaluation_metrics.json", {}).get("human_review_queue", [])
