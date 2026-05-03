#!/usr/bin/env python3
"""Transcript Intelligence take-home pipeline.

This script intentionally avoids hosted services so the analysis is repeatable
from the submitted repository. It uses a transparent hybrid approach:

1. The provided transcript summaries/topics/key moments supply compact semantic
   signals.
2. Rule-based scoring maps each call to a business theme and call type.
3. Transcript-level sentiment labels are aggregated to validate and enrich the
   provided meeting-level sentiment score.

Run:
    python3 src/analyze_transcripts.py --dataset dataset --output outputs
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


THEMES: dict[str, list[str]] = {
    "Incident & Reliability": [
        "outage",
        "incident",
        "latency",
        "slow",
        "timeout",
        "dashboard down",
        "alerts not firing",
        "alert delays",
        "performance",
        "reliability",
        "root cause",
        "post-incident",
    ],
    "Compliance & Audit": [
        "comply",
        "compliance",
        "soc 2",
        "hipaa",
        "audit",
        "template",
        "on-demand reporting",
        "iso 27001",
        "pci dss",
    ],
    "Backup & Recovery": [
        "backup",
        "restore",
        "recovery",
        "rto",
        "rpo",
        "cloudprime",
        "protect",
        "backup window",
    ],
    "Identity & Access": [
        "identity",
        "ldap",
        "sso",
        "mfa",
        "authentication",
        "account recovery",
        "policy sync",
    ],
    "Product Feedback & Roadmap": [
        "roadmap",
        "feedback",
        "design review",
        "launch readiness",
        "deployment",
        "ga deployment",
        "sprint",
        "planning",
        "quarterly planning",
        "feature",
    ],
    "Renewal & Commercial Risk": [
        "renewal",
        "billing",
        "invoice",
        "pricing",
        "qbr",
        "business review",
        "multi-year",
        "commercial",
        "adoption",
        "platform concerns",
        "contract",
        "annual review",
        "account review",
    ],
    "Competitive & Market": [
        "competitive",
        "competitor",
        "sentinelshield",
        "vaultedge",
        "cybernova",
        "fortiguard",
        "evaluation",
        "landscape",
        "threat",
    ],
}

TITLE_THEME_RULES = [
    ("Competitive & Market", ["competitive", "win/loss", "vendor comparison"]),
    ("Identity & Access", ["identity", "ldap", "sso", "mfa", "saml", "scim", "account recovery"]),
    ("Incident & Reliability", ["outage", "incident", "latency", "timeout", "dashboard down", "alerts not firing", "data gaps", "false positives", "performance", "slow", "failure", "bug"]),
    ("Backup & Recovery", ["backup", "restore", "recovery", "protect", "cloudprime"]),
    ("Compliance & Audit", ["comply", "compliance", "soc 2", "hipaa", "audit", "iso 27001", "pci dss"]),
    ("Renewal & Commercial Risk", ["renewal", "billing", "invoice", "contract", "annual review", "business review", "q1 business review", "q2 planning", "account review", "platform concerns", "license", "overage"]),
    ("Product Feedback & Roadmap", ["roadmap", "feedback", "design review", "launch", "deployment", "sprint", "planning", "all hands", "standup"]),
]

PRODUCT_KEYWORDS: dict[str, list[str]] = {
    "Detect": ["detect", "alerts", "logvault", "siem", "dashboard", "latency", "outage", "sentinelshield", "threat visibility"],
    "Comply": ["comply", "compliance", "soc 2", "hipaa", "audit", "report", "template"],
    "Protect": ["protect", "backup", "restore", "recovery", "rto", "rpo", "cloudprime"],
    "Identity": ["identity", "ldap", "sso", "mfa", "authentication", "account recovery", "role", "roles", "permissions", "rbac"],
}

NEGATIVE_SIGNALS = [
    "outage",
    "urgent",
    "escalation",
    "concern",
    "risk",
    "delay",
    "failure",
    "timeout",
    "slow",
    "down",
    "not firing",
    "impact",
    "frustrated",
    "gap",
]


@dataclass
class MeetingAnalysis:
    meeting_id: str
    title: str
    call_type: str
    primary_theme: str
    secondary_theme: str
    products: str
    start_time: str
    duration_minutes: float
    attendee_count: int
    transcript_utterances: int
    sentiment_score: float
    overall_sentiment: str
    transcript_sentiment_score: float
    negative_utterance_share: float
    positive_utterance_share: float
    action_item_count: int
    key_moment_count: int
    risk_score: int
    topics: str
    summary: str
    example_quote: str
    cluster_id: int = -1
    cluster_terms: str = ""
    cluster_label: str = ""
    theme_confidence: float = 0.0


STOPWORDS = {
    "a",
    "about",
    "across",
    "after",
    "again",
    "aegis",
    "aegiscloud",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "call",
    "calls",
    "can",
    "case",
    "customer",
    "customers",
    "for",
    "from",
    "had",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "meeting",
    "more",
    "not",
    "of",
    "on",
    "or",
    "our",
    "out",
    "over",
    "review",
    "so",
    "support",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "with",
    "would",
    # Frequent participant/customer first names add noise to unsupervised terms.
    "alex",
    "david",
    "emily",
    "jordan",
    "marcus",
    "maria",
    "sarah",
    "thomas",
    "tom",
    "victor",
    "wayne",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(*parts: Any) -> str:
    flattened: list[str] = []
    for part in parts:
        if isinstance(part, str):
            flattened.append(part)
        elif isinstance(part, list):
            flattened.extend(str(x) for x in part)
        elif isinstance(part, dict):
            flattened.extend(str(x) for x in part.values())
        elif part is not None:
            flattened.append(str(part))
    return " ".join(flattened).lower()


def classify_call_type(title: str, emails: list[str]) -> str:
    t = title.lower()
    if t.startswith("support case") or "urgent:" in t or "escalation:" in t:
        return "Customer support"
    if "aegis /" in t:
        return "External customer"
    if any(marker in t for marker in ["all hands", "team", "internal", "sprint", "root cause", "post-incident", "deployment plan", "launch readiness"]):
        return "Internal"
    external_domains = {email.split("@")[-1] for email in emails if "@" in email}
    if len(external_domains) > 1:
        return "External customer"
    return "Internal"


def score_keywords(text: str, keyword_map: dict[str, list[str]]) -> Counter:
    scores: Counter = Counter()
    for label, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in text:
                scores[label] += 2 if " " in keyword else 1
    return scores


def top_two_theme(text: str) -> tuple[str, str]:
    title = text.split(" || ", 1)[0]
    title_hits: list[str] = []
    for label, patterns in TITLE_THEME_RULES:
        if any(pattern in title for pattern in patterns):
            title_hits.append(label)
    if title_hits:
        secondary = title_hits[1] if len(title_hits) > 1 else "None"
        return title_hits[0], secondary

    scores = score_keywords(text, THEMES)
    if not scores:
        return "General Operations", "Unclassified"
    ordered = scores.most_common()
    primary = ordered[0][0]
    secondary = ordered[1][0] if len(ordered) > 1 else "None"
    return primary, secondary


def theme_confidence(text: str, primary_theme: str) -> float:
    """Approximate classifier confidence from keyword margin.

    Low-confidence rows are natural candidates for human review or an LLM
    adjudication step in a production workflow.
    """
    title = text.split(" || ", 1)[0]
    for label, patterns in TITLE_THEME_RULES:
        if label == primary_theme and any(pattern in title for pattern in patterns):
            return 0.86

    scores = score_keywords(text, THEMES)
    if not scores:
        return 0.0
    ordered = scores.most_common()
    top = scores.get(primary_theme, ordered[0][1])
    runner_up = ordered[1][1] if len(ordered) > 1 else 0
    confidence = (top - runner_up + 1) / (top + 1)
    return round(max(0.1, min(0.99, confidence)), 2)


def product_tags(text: str) -> list[str]:
    title = text.split(" || ", 1)[0]
    title_product_rules = [
        ("Detect", ["detect", "outage", "logvault", "siem", "alert", "threat visibility", "threat detection"]),
        ("Comply", ["comply", "compliance", "soc 2", "hipaa", "audit", "iso 27001", "pci dss"]),
        ("Protect", ["protect", "backup", "restore", "recovery", "cloudprime"]),
        ("Identity", ["identity", "ldap", "sso", "mfa", "saml", "scim", "account recovery"]),
    ]
    title_products = [label for label, patterns in title_product_rules if any(pattern in title for pattern in patterns)]
    scores = score_keywords(text, PRODUCT_KEYWORDS)
    if not scores:
        return title_products or ["Platform"]
    max_score = scores.most_common(1)[0][1]
    scored_products = [label for label, score in scores.most_common() if score >= max(2, max_score * 0.35)]
    ordered = title_products + [label for label in scored_products if label not in title_products]
    return ordered or [scores.most_common(1)[0][0]]


def sentiment_from_transcript(utterances: list[dict[str, Any]]) -> tuple[float, float, float]:
    values = {"positive": 1, "neutral": 0, "negative": -1}
    if not utterances:
        return 0.0, 0.0, 0.0
    counts = Counter((u.get("sentimentType") or "neutral").lower() for u in utterances)
    total = sum(counts.values())
    score = sum(values.get(label, 0) * count for label, count in counts.items()) / total
    return score, counts["negative"] / total, counts["positive"] / total


def choose_quote(utterances: list[dict[str, Any]], theme: str) -> str:
    theme_words = THEMES.get(theme, []) + NEGATIVE_SIGNALS
    candidates = []
    for utt in utterances:
        sentence = utt.get("sentence", "")
        lower = sentence.lower()
        if len(sentence) < 45:
            continue
        score = sum(1 for word in theme_words if word in lower)
        if utt.get("sentimentType") == "negative":
            score += 2
        if score:
            candidates.append((score, sentence))
    if not candidates and utterances:
        candidates = [(0, u.get("sentence", "")) for u in utterances if len(u.get("sentence", "")) >= 45]
    quote = max(candidates, default=(0, ""))[1]
    return quote[:240]


def risk_score(text: str, neg_share: float, action_items: list[str]) -> int:
    signal_hits = sum(1 for signal in NEGATIVE_SIGNALS if signal in text)
    raw = signal_hits + int(neg_share * 20) + min(len(action_items), 5)
    return min(10, raw)


def analyze_meeting(folder: Path) -> MeetingAnalysis:
    meeting = load_json(folder / "meeting-info.json")
    summary = load_json(folder / "summary.json")
    transcript = load_json(folder / "transcript.json").get("data", [])

    title = meeting.get("title", "")
    emails = meeting.get("allEmails", [])
    text = normalize_text(
        f"{title} ||",
        summary.get("summary"),
        summary.get("topics", []),
        summary.get("keyMoments", []),
        summary.get("actionItems", []),
        [u.get("sentence", "") for u in transcript],
    )
    primary, secondary = top_two_theme(text)
    transcript_score, neg_share, pos_share = sentiment_from_transcript(transcript)
    action_items = summary.get("actionItems", [])

    return MeetingAnalysis(
        meeting_id=meeting.get("meetingId", folder.name),
        title=title,
        call_type=classify_call_type(title, emails),
        primary_theme=primary,
        secondary_theme=secondary,
        products=", ".join(product_tags(text)),
        start_time=meeting.get("startTime", ""),
        duration_minutes=round(float(meeting.get("duration", 0.0)), 1),
        attendee_count=len(emails),
        transcript_utterances=len(transcript),
        sentiment_score=float(summary.get("sentimentScore", 0.0)),
        overall_sentiment=summary.get("overallSentiment", "unknown"),
        transcript_sentiment_score=round(transcript_score, 3),
        negative_utterance_share=round(neg_share, 3),
        positive_utterance_share=round(pos_share, 3),
        action_item_count=len(action_items),
        key_moment_count=len(summary.get("keyMoments", [])),
        risk_score=risk_score(text, neg_share, action_items),
        topics=", ".join(summary.get("topics", [])),
        summary=summary.get("summary", ""),
        example_quote=choose_quote(transcript, primary),
        theme_confidence=theme_confidence(text, primary),
    )


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9]+", text.lower())
    unigrams = [w for w in words if len(w) > 2 and w not in STOPWORDS]
    bigrams = [f"{a}_{b}" for a, b in zip(unigrams, unigrams[1:]) if a != b]
    return unigrams + bigrams


def cosine_distance(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(value * b.get(term, 0.0) for term, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - dot / (norm_a * norm_b)


def mean_vector(vectors: list[dict[str, float]]) -> dict[str, float]:
    if not vectors:
        return {}
    totals: Counter = Counter()
    for vector in vectors:
        totals.update(vector)
    return {term: value / len(vectors) for term, value in totals.items()}


def tfidf_vectors(rows: list[MeetingAnalysis]) -> list[dict[str, float]]:
    docs = [tokenize(f"{row.title} {row.topics} {row.summary} {row.example_quote}") for row in rows]
    df: Counter = Counter()
    for tokens in docs:
        df.update(set(tokens))
    total_docs = len(docs)
    vectors: list[dict[str, float]] = []
    for tokens in docs:
        counts = Counter(tokens)
        max_count = max(counts.values() or [1])
        vector = {}
        for term, count in counts.items():
            tf = count / max_count
            idf = math.log((1 + total_docs) / (1 + df[term])) + 1
            vector[term] = tf * idf
        vectors.append(vector)
    return vectors


def add_discovery_clusters(rows: list[MeetingAnalysis], cluster_count: int = 7) -> list[dict[str, Any]]:
    """Cluster meetings with a tiny deterministic TF-IDF k-means experiment.

    This is not meant to beat a mature embedding model. It is a dependency-free
    discovery check that shows whether unsupervised text structure roughly
    agrees with, or challenges, the hand-built business taxonomy.
    """
    if not rows:
        return []

    k = min(cluster_count, max(2, int(math.sqrt(len(rows)))))
    vectors = tfidf_vectors(rows)

    # Deterministic initialization: spread seeds across the sorted corpus.
    seed_indexes = [round(i * (len(rows) - 1) / max(k - 1, 1)) for i in range(k)]
    centers = [vectors[index] for index in seed_indexes]
    assignments = [0] * len(rows)

    for _ in range(20):
        changed = False
        for i, vector in enumerate(vectors):
            best_cluster = min(range(k), key=lambda cluster: cosine_distance(vector, centers[cluster]))
            if assignments[i] != best_cluster:
                assignments[i] = best_cluster
                changed = True
        grouped_vectors = [[vectors[i] for i, cluster in enumerate(assignments) if cluster == c] for c in range(k)]
        centers = [mean_vector(group) if group else centers[c] for c, group in enumerate(grouped_vectors)]
        if not changed:
            break

    cluster_summaries: list[dict[str, Any]] = []
    for cluster in range(k):
        indexes = [i for i, assigned in enumerate(assignments) if assigned == cluster]
        if not indexes:
            continue
        center = centers[cluster]
        top_terms = [
            term.replace("_", " ")
            for term, _ in sorted(center.items(), key=lambda item: item[1], reverse=True)[:8]
        ]
        theme_counts = Counter(rows[i].primary_theme for i in indexes)
        call_type_counts = Counter(rows[i].call_type for i in indexes)
        label = top_terms[0].title() if top_terms else f"Cluster {cluster}"
        for i in indexes:
            rows[i].cluster_id = cluster
            rows[i].cluster_terms = ", ".join(top_terms)
            rows[i].cluster_label = label
        cluster_rows = [rows[i] for i in indexes]
        cluster_summaries.append(
            {
                "cluster_id": cluster,
                "cluster_label": label,
                "meetings": len(indexes),
                "top_terms": ", ".join(top_terms),
                "dominant_theme": theme_counts.most_common(1)[0][0],
                "dominant_call_type": call_type_counts.most_common(1)[0][0],
                "avg_sentiment_score": round(statistics.mean(row.sentiment_score for row in cluster_rows), 2),
                "avg_risk_score": round(statistics.mean(row.risk_score for row in cluster_rows), 2),
                "example_meetings": [row.title for row in cluster_rows[:3]],
            }
        )
    return sorted(cluster_summaries, key=lambda row: (-row["meetings"], row["cluster_id"]))


def search_similar(rows: list[MeetingAnalysis], query: str, limit: int = 5) -> list[dict[str, Any]]:
    corpus_vectors = tfidf_vectors(rows + [MeetingAnalysis(
        meeting_id="query",
        title=query,
        call_type="",
        primary_theme="",
        secondary_theme="",
        products="",
        start_time="",
        duration_minutes=0.0,
        attendee_count=0,
        transcript_utterances=0,
        sentiment_score=0.0,
        overall_sentiment="",
        transcript_sentiment_score=0.0,
        negative_utterance_share=0.0,
        positive_utterance_share=0.0,
        action_item_count=0,
        key_moment_count=0,
        risk_score=0,
        topics="",
        summary=query,
        example_quote="",
    )])
    query_vector = corpus_vectors[-1]
    scored = []
    for row, vector in zip(rows, corpus_vectors[:-1]):
        score = 1 - cosine_distance(query_vector, vector)
        scored.append((score, row))
    results = []
    for score, row in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]:
        results.append(
            {
                "query": query,
                "similarity": round(score, 3),
                "meeting_id": row.meeting_id,
                "title": row.title,
                "call_type": row.call_type,
                "theme": row.primary_theme,
                "products": row.products,
                "risk_score": row.risk_score,
                "sentiment_score": row.sentiment_score,
                "evidence_quote": row.example_quote,
            }
        )
    return results


def generate_semantic_search_examples(rows: list[MeetingAnalysis]) -> list[dict[str, Any]]:
    queries = [
        "Which calls show Detect reliability or outage risk?",
        "Where do customers mention renewal risk, pricing, or competitive evaluation?",
        "What product gaps should product managers prioritize?",
        "Which compliance or audit conversations need roadmap follow-up?",
        "Which identity and access issues are creating customer friction?",
    ]
    examples: list[dict[str, Any]] = []
    for query in queries:
        examples.extend(search_similar(rows, query, limit=5))
    return examples


def evaluate_taxonomy(rows: list[MeetingAnalysis], cluster_summary: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    low_confidence = [row for row in rows if row.theme_confidence < 0.35]
    cluster_purity_values = []
    for cluster in cluster_summary:
        cluster_rows = [row for row in rows if row.cluster_id == cluster["cluster_id"]]
        if not cluster_rows:
            continue
        dominant_count = Counter(row.primary_theme for row in cluster_rows).most_common(1)[0][1]
        cluster_purity_values.append(dominant_count / len(cluster_rows))

    return {
        "meeting_count": total,
        "theme_count": len(set(row.primary_theme for row in rows)),
        "cluster_count": len(cluster_summary),
        "avg_theme_confidence": round(statistics.mean(row.theme_confidence for row in rows), 2),
        "low_confidence_meetings": len(low_confidence),
        "low_confidence_share": round(len(low_confidence) / total, 3) if total else 0.0,
        "avg_cluster_purity": round(statistics.mean(cluster_purity_values), 2) if cluster_purity_values else 0.0,
        "human_review_queue": [
            {
                "title": row.title,
                "theme": row.primary_theme,
                "confidence": row.theme_confidence,
                "cluster_label": row.cluster_label,
                "risk_score": row.risk_score,
            }
            for row in sorted(low_confidence, key=lambda row: (row.theme_confidence, -row.risk_score, row.title))[:10]
        ],
    }


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def evaluate_against_gold(rows: list[MeetingAnalysis], gold_path: Path | None) -> dict[str, Any]:
    if not gold_path or not gold_path.exists():
        return {"available": False, "message": "No gold label file provided."}

    by_id = {row.meeting_id: row for row in rows}
    gold_rows = []
    with gold_path.open("r", encoding="utf-8", newline="") as f:
        gold_rows = list(csv.DictReader(f))

    evaluated = []
    for gold in gold_rows:
        predicted = by_id.get(gold["meeting_id"])
        if not predicted:
            continue
        predicted_product = predicted.products.split(", ")[0]
        predicted_high_risk = predicted.risk_score >= 8
        expected_high_risk = gold["expected_high_risk"].lower() == "true"
        evaluated.append(
            {
                "meeting_id": gold["meeting_id"],
                "title": predicted.title,
                "expected_call_type": gold["expected_call_type"],
                "predicted_call_type": predicted.call_type,
                "call_type_correct": gold["expected_call_type"] == predicted.call_type,
                "expected_primary_theme": gold["expected_primary_theme"],
                "predicted_primary_theme": predicted.primary_theme,
                "theme_correct": gold["expected_primary_theme"] == predicted.primary_theme,
                "expected_primary_product": gold["expected_primary_product"],
                "predicted_primary_product": predicted_product,
                "product_correct": gold["expected_primary_product"] == predicted_product,
                "expected_high_risk": expected_high_risk,
                "predicted_high_risk": predicted_high_risk,
                "risk_correct": expected_high_risk == predicted_high_risk,
            }
        )

    def accuracy(field: str) -> float:
        if not evaluated:
            return 0.0
        return round(sum(1 for row in evaluated if row[field]) / len(evaluated), 3)

    high_risk_tp = sum(1 for row in evaluated if row["expected_high_risk"] and row["predicted_high_risk"])
    high_risk_fp = sum(1 for row in evaluated if not row["expected_high_risk"] and row["predicted_high_risk"])
    high_risk_fn = sum(1 for row in evaluated if row["expected_high_risk"] and not row["predicted_high_risk"])

    return {
        "available": True,
        "gold_label_count": len(evaluated),
        "call_type_accuracy": accuracy("call_type_correct"),
        "theme_accuracy": accuracy("theme_correct"),
        "product_accuracy": accuracy("product_correct"),
        "risk_accuracy": accuracy("risk_correct"),
        "high_risk_detection": precision_recall_f1(high_risk_tp, high_risk_fp, high_risk_fn),
        "rows": evaluated,
    }


def aggregate(rows: list[MeetingAnalysis]) -> dict[str, Any]:
    by_type: dict[str, list[MeetingAnalysis]] = defaultdict(list)
    by_theme: dict[str, list[MeetingAnalysis]] = defaultdict(list)
    by_product: dict[str, list[MeetingAnalysis]] = defaultdict(list)
    for row in rows:
        by_type[row.call_type].append(row)
        by_theme[row.primary_theme].append(row)
        for product in row.products.split(", "):
            by_product[product].append(row)

    def avg(values: list[float]) -> float:
        return round(statistics.mean(values), 2) if values else 0.0

    return {
        "meeting_count": len(rows),
        "call_type_summary": [
            {
                "call_type": key,
                "meetings": len(vals),
                "avg_sentiment_score": avg([v.sentiment_score for v in vals]),
                "negative_utterance_share": round(statistics.mean(v.negative_utterance_share for v in vals), 3),
                "avg_risk_score": avg([v.risk_score for v in vals]),
                "avg_action_items": avg([v.action_item_count for v in vals]),
            }
            for key, vals in sorted(by_type.items())
        ],
        "theme_summary": [
            {
                "theme": key,
                "meetings": len(vals),
                "avg_sentiment_score": avg([v.sentiment_score for v in vals]),
                "avg_risk_score": avg([v.risk_score for v in vals]),
                "example_meetings": [v.title for v in vals[:3]],
            }
            for key, vals in sorted(by_theme.items(), key=lambda item: (-len(item[1]), item[0]))
        ],
        "product_summary": [
            {
                "product": key,
                "meetings": len(vals),
                "avg_sentiment_score": avg([v.sentiment_score for v in vals]),
                "avg_risk_score": avg([v.risk_score for v in vals]),
            }
            for key, vals in sorted(by_product.items(), key=lambda item: (-len(item[1]), item[0]))
        ],
        "highest_risk_meetings": [
            {
                "title": r.title,
                "call_type": r.call_type,
                "theme": r.primary_theme,
                "risk_score": r.risk_score,
                "sentiment_score": r.sentiment_score,
                "why": r.summary[:260],
            }
            for r in sorted(rows, key=lambda r: (-r.risk_score, r.sentiment_score, r.title))[:10]
        ],
    }


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str] | None = None) -> None:
    if not fieldnames:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def bar_svg(items: list[tuple[str, float]], title: str, path: Path, color: str = "#2F6F73") -> None:
    width, height = 980, 520
    left, top, bar_h, gap = 260, 80, 34, 18
    max_value = max([v for _, v in items] or [1])
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#F7F4ED"/>',
        f'<text x="40" y="44" font-family="Arial" font-size="28" font-weight="700" fill="#182322">{html.escape(title)}</text>',
    ]
    for i, (label, value) in enumerate(items):
        y = top + i * (bar_h + gap)
        bar_w = 1 if max_value == 0 else (value / max_value) * (width - left - 90)
        lines.append(f'<text x="40" y="{y + 24}" font-family="Arial" font-size="17" fill="#243130">{html.escape(label)}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="4" fill="{color}"/>')
        lines.append(f'<text x="{left + bar_w + 12:.1f}" y="{y + 24}" font-family="Arial" font-size="17" font-weight="700" fill="#243130">{value:g}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_report(
    rows: list[MeetingAnalysis],
    summary: dict[str, Any],
    cluster_summary: list[dict[str, Any]],
    evaluation: dict[str, Any],
    gold_evaluation: dict[str, Any],
    path: Path,
) -> None:
    theme_lines = []
    for item in summary["theme_summary"]:
        examples = "; ".join(item["example_meetings"])
        theme_lines.append(
            f"| {item['theme']} | {item['meetings']} | {item['avg_sentiment_score']} | {item['avg_risk_score']} | {examples} |"
        )

    type_lines = [
        f"| {item['call_type']} | {item['meetings']} | {item['avg_sentiment_score']} | {item['negative_utterance_share']:.1%} | {item['avg_risk_score']} |"
        for item in summary["call_type_summary"]
    ]

    high_risk = "\n".join(
        f"- **{item['title']}** ({item['call_type']}, {item['theme']}): risk {item['risk_score']}/10, sentiment {item['sentiment_score']}. {item['why']}"
        for item in summary["highest_risk_meetings"][:6]
    )

    cluster_lines = [
        f"| {item['cluster_id']} | {item['meetings']} | {item['top_terms']} | {item['dominant_theme']} | {item['avg_risk_score']} |"
        for item in cluster_summary
    ]

    review_queue = "\n".join(
        f"- **{item['title']}**: {item['theme']} at {item['confidence']:.0%} confidence, cluster `{item['cluster_label']}`, risk {item['risk_score']}/10"
        for item in evaluation["human_review_queue"][:6]
    ) or "- No low-confidence items found."

    if gold_evaluation.get("available"):
        gold_section = f"""
## Gold-Label Evaluation

I added a curated 20-meeting gold-label sample to evaluate the pipeline like an AI system, not just a dashboard.

- Call type accuracy: **{gold_evaluation['call_type_accuracy']:.0%}**
- Theme accuracy: **{gold_evaluation['theme_accuracy']:.0%}**
- Product accuracy: **{gold_evaluation['product_accuracy']:.0%}**
- Risk routing accuracy: **{gold_evaluation['risk_accuracy']:.0%}**
- High-risk detection F1: **{gold_evaluation['high_risk_detection']['f1']:.0%}**

This is deliberately small, but it establishes the evaluation harness. The production version should expand this into a labeled validation set with precision/recall by theme, reviewer agreement, and drift monitoring.
"""
    else:
        gold_section = ""

    content = f"""# Transcript Intelligence Analysis

## Executive Takeaways

- The 100-call sample is best treated as a mixed operating signal, not just a transcript archive: customer support exposes acute defects, external customer calls expose renewal and adoption risk, and internal calls show how the organization prioritizes the work.
- Incident/reliability and compliance/audit conversations carry the highest operating risk. They combine negative sentiment, escalations, and many follow-up actions.
- Sentiment is most useful when read by call type. Customer support calls are predictably more negative, but external customer calls with only moderately negative language can be more commercially important because they connect product gaps to renewals, competitive evaluations, and trust.
- The highest-value product opportunity is a workflow that connects transcript themes to owner-ready next steps: product area, customer/account, evidence quote, risk level, and action item.

## Approach

I used a transparent hybrid pipeline rather than a black-box LLM pass. The provided summaries, topics, key moments, and utterance-level sentiment are used as semantic input. A rule-based scoring layer then classifies each meeting into call type, primary theme, product surface, and risk score. I also added a lightweight TF-IDF k-means clustering experiment as a discovery check: it helps show whether unsupervised text structure agrees with the business taxonomy, without requiring external APIs or heavy dependencies.

## Theme Categories

| Theme | Meetings | Avg sentiment | Avg risk | Example transcripts |
|---|---:|---:|---:|---|
{chr(10).join(theme_lines)}

## Sentiment by Call Type

| Call type | Meetings | Avg sentiment | Negative utterance share | Avg risk |
|---|---:|---:|---:|---:|
{chr(10).join(type_lines)}

## Meetings Worth Leadership Attention

{high_risk}

## ML Discovery Experiment: TF-IDF Clusters

The clustering layer is not the production classifier; it is an exploratory check. It groups meetings by unsupervised text similarity, then compares each cluster to the hand-labeled business theme. This is useful for finding emerging pockets of language that rules might miss.

| Cluster | Meetings | Top terms | Dominant business theme | Avg risk |
|---:|---:|---|---|---:|
{chr(10).join(cluster_lines)}

## AI Evaluation and Human Review

To make the system more AI-ready, the pipeline now reports lightweight evaluation metrics and a review queue.

- Average theme confidence: **{evaluation['avg_theme_confidence']:.0%}**
- Low-confidence meetings: **{evaluation['low_confidence_meetings']}** ({evaluation['low_confidence_share']:.1%})
- Average cluster purity against rule labels: **{evaluation['avg_cluster_purity']:.0%}**

Human review queue:

{review_queue}

{gold_section}

## Additional Insight Ideas

1. **Revenue risk heatmap for sales and CS leaders.** Combine renewal language, competitor mentions, negative sentiment, and account names to flag customers where product friction is turning into commercial risk.
2. **Product gap backlog generator for PMs.** Convert repeated pain points into ranked themes with direct quotes, affected accounts, current owner, and estimated urgency.
3. **Incident learning loop for engineering leads.** Link outage/support conversations to post-incident/internal planning calls to verify whether customer pain is making it into reliability work.
4. **Launch readiness monitor.** Track whether internal launch confidence aligns with customer-facing questions and support cases after GA.

## Limitations and Next Steps

- The classifier is intentionally explainable. The included TF-IDF clustering is a lightweight experiment; in production, I would replace or augment it with embeddings or an LLM labeling step, then keep the rules as guardrails and audit checks.
- Sentiment labels are sentence-level and do not distinguish politeness from business risk. The risk score corrects for this by incorporating escalations, action items, and negative operational terms.
- Account and owner extraction could be made more precise with named entity recognition or CRM enrichment.
"""
    path.write_text(content, encoding="utf-8")


def write_html_dashboard(rows: list[MeetingAnalysis], summary: dict[str, Any], path: Path) -> None:
    cards = "\n".join(
        f"""<article><h3>{html.escape(item['theme'])}</h3><strong>{item['meetings']}</strong><span>meetings</span><p>Avg risk {item['avg_risk_score']} / sentiment {item['avg_sentiment_score']}</p></article>"""
        for item in summary["theme_summary"][:7]
    )
    risks = "\n".join(
        f"""<tr><td>{html.escape(item['title'])}</td><td>{html.escape(item['call_type'])}</td><td>{html.escape(item['theme'])}</td><td>{item['risk_score']}</td><td>{item['sentiment_score']}</td></tr>"""
        for item in summary["highest_risk_meetings"][:10]
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Transcript Intelligence Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f7f4ed; color: #182322; }}
    header {{ padding: 42px 52px 24px; background: #183331; color: white; }}
    h1 {{ margin: 0; font-size: 42px; letter-spacing: 0; }}
    header p {{ max-width: 980px; color: #dbe7e3; font-size: 18px; line-height: 1.45; }}
    main {{ padding: 34px 52px 52px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    article {{ background: white; border: 1px solid #d8d1c3; border-radius: 8px; padding: 18px; min-height: 140px; }}
    article h3 {{ margin: 0 0 16px; font-size: 18px; }}
    article strong {{ font-size: 42px; display: block; color: #2f6f73; }}
    article span {{ text-transform: uppercase; letter-spacing: .08em; color: #6a716c; font-size: 12px; }}
    section {{ margin-top: 34px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8d1c3; }}
    th, td {{ text-align: left; padding: 12px 14px; border-bottom: 1px solid #e8e1d5; font-size: 14px; }}
    th {{ background: #eee7da; }}
    img {{ max-width: 100%; background: white; border: 1px solid #d8d1c3; border-radius: 8px; }}
  </style>
</head>
<body>
  <header>
    <h1>Transcript Intelligence</h1>
    <p>Hybrid analysis of 100 call transcripts across support, customer, and internal conversations. The pipeline turns raw transcripts into theme, sentiment, product, and risk signals for product and engineering leaders.</p>
  </header>
  <main>
    <div class="grid">{cards}</div>
    <section>
      <h2>Theme Volume</h2>
      <img src="theme_counts.svg" alt="Theme counts chart">
    </section>
    <section>
      <h2>Highest Risk Meetings</h2>
      <table><thead><tr><th>Meeting</th><th>Call type</th><th>Theme</th><th>Risk</th><th>Sentiment</th></tr></thead><tbody>{risks}</tbody></table>
    </section>
  </main>
</body>
</html>
"""
    path.write_text(html_doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="dataset", type=Path)
    parser.add_argument("--output", default="outputs", type=Path)
    parser.add_argument("--gold-labels", default=Path("evaluation/gold_labels.csv"), type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    rows = [analyze_meeting(folder) for folder in sorted(args.dataset.iterdir()) if folder.is_dir()]
    cluster_summary = add_discovery_clusters(rows)
    evaluation = evaluate_taxonomy(rows, cluster_summary)
    gold_path = args.gold_labels
    if not gold_path.is_absolute():
        gold_path = Path.cwd() / gold_path
    gold_evaluation = evaluate_against_gold(rows, gold_path)
    semantic_examples = generate_semantic_search_examples(rows)
    summary = aggregate(rows)

    row_dicts = [asdict(row) for row in rows]
    write_csv(row_dicts, args.output / "meeting_analysis.csv")
    (args.output / "meeting_analysis.json").write_text(json.dumps(row_dicts, indent=2), encoding="utf-8")
    (args.output / "summary_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.output / "cluster_summary.json").write_text(json.dumps(cluster_summary, indent=2), encoding="utf-8")
    (args.output / "evaluation_metrics.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    (args.output / "gold_label_evaluation.json").write_text(json.dumps(gold_evaluation, indent=2), encoding="utf-8")
    (args.output / "semantic_search_examples.json").write_text(json.dumps(semantic_examples, indent=2), encoding="utf-8")
    write_csv(summary["theme_summary"], args.output / "theme_summary.csv")
    write_csv(summary["call_type_summary"], args.output / "call_type_summary.csv")
    write_csv(summary["product_summary"], args.output / "product_summary.csv")
    write_csv(cluster_summary, args.output / "cluster_summary.csv")
    write_csv(semantic_examples, args.output / "semantic_search_examples.csv")
    write_csv(evaluation["human_review_queue"], args.output / "human_review_queue.csv")
    if gold_evaluation.get("available"):
        write_csv(gold_evaluation["rows"], args.output / "gold_label_evaluation.csv")

    bar_svg([(x["theme"], x["meetings"]) for x in summary["theme_summary"]], "Meetings by Primary Theme", args.output / "theme_counts.svg")
    bar_svg(
        [(x["call_type"], x["negative_utterance_share"] * 100) for x in summary["call_type_summary"]],
        "Negative Utterance Share by Call Type",
        args.output / "negative_sentiment_by_call_type.svg",
        color="#9B4D45",
    )
    bar_svg(
        [(x["product"], x["avg_risk_score"]) for x in summary["product_summary"]],
        "Average Risk Score by Product Surface",
        args.output / "product_risk.svg",
        color="#C48A2C",
    )
    bar_svg(
        [(f"C{x['cluster_id']}: {x['cluster_label']}", x["meetings"]) for x in cluster_summary],
        "Unsupervised TF-IDF Cluster Sizes",
        args.output / "cluster_counts.svg",
        color="#4F7B58",
    )
    write_markdown_report(rows, summary, cluster_summary, evaluation, gold_evaluation, args.output / "analysis_report.md")
    write_html_dashboard(rows, summary, args.output / "dashboard.html")

    print(f"Analyzed {len(rows)} meetings")
    print(f"Wrote outputs to {args.output}")


if __name__ == "__main__":
    main()
