# Transcript Intelligence Take-Home

This repository contains a complete, reproducible analysis of the provided transcript dataset for the Transcript Intelligence assessment.

## Deliverables

- Technical pipeline and reference material:
  - `src/analyze_transcripts.py`
  - `src/embedding_retrieval.py`
  - `src/app.py`
  - `outputs/analysis_report.md`
  - `outputs/dashboard.html`
  - `outputs/meeting_analysis.csv`
  - `outputs/summary_metrics.json`
- Video demo support: `docs/video_demo_script.md`

The stakeholder slide deck and video recording are submitted separately from this code repository.

## How to Run

From this folder:

```bash
python3 src/analyze_transcripts.py --dataset dataset --output outputs
```

The analysis pipeline has no required third-party Python dependencies. It uses the supplied JSON files directly.

Optional real embeddings:

```bash
OPENAI_API_KEY=your_key_here \
  python3 src/embedding_retrieval.py \
  --meetings outputs/meeting_analysis.json \
  --output outputs
```

This uses OpenAI `text-embedding-3-small` by default. If `OPENAI_API_KEY` is not set, the script writes `outputs/real_embedding_status.json` with a skipped status so the repo remains reproducible.

Optional FastAPI review app:

```bash
python3 -m pip install -r requirements-optional.txt
uvicorn src.app:app --reload --app-dir .
```

Useful endpoints:

- `GET /summary`
- `GET /meetings?min_risk=8`
- `GET /search-examples`
- `GET /review-queue`

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Approach

I used a transparent hybrid approach:

1. Read each meeting folder and combine the transcript, summary, topics, key moments, and action items.
2. Classify each meeting by call type: customer support, external customer, or internal.
3. Score each meeting into one primary business theme and product surface using explainable keyword rules.
4. Run a lightweight TF-IDF k-means clustering experiment to test whether unsupervised text structure agrees with the business taxonomy.
5. Build a small semantic retrieval layer for RAG-style stakeholder questions and evidence quotes.
6. Generate AI evaluation signals: taxonomy confidence, cluster purity, and a human-review queue.
7. Evaluate the pipeline against a curated gold-label sample with accuracy and high-risk precision/recall/F1.
8. Aggregate utterance-level sentiment, provided meeting sentiment, action items, and risk signals.
9. Generate CSV/JSON outputs, an HTML dashboard, SVG charts, and a written report.

This is intentionally explainable for an interview panel. In production, I would add embedding clustering or LLM-assisted labeling, then keep the rule layer as an audit and routing guardrail.

## Key Findings

- Reliability and incident conversations are the highest-risk theme: they combine urgent language, customer impact, and concrete technical follow-up.
- Customer support has the highest negative utterance share, but external customer calls matter commercially because they connect product issues to renewals, competitive evaluations, and roadmap confidence.
- Detect is the most urgent product surface to operationalize first because outage, alerting, SIEM connector, and competitive signals recur across call types.
- The most valuable product workflow is not just charts; it is owner-ready routing: product surface, account, evidence quote, risk score, and recommended next action.

## Important Files

- `outputs/theme_summary.csv`: theme counts, average sentiment, risk, and example meetings.
- `outputs/call_type_summary.csv`: sentiment and risk by support, external, and internal calls.
- `outputs/product_summary.csv`: product-level risk signal.
- `outputs/cluster_summary.csv`: dependency-free TF-IDF clustering experiment with top terms and dominant themes.
- `outputs/semantic_search_examples.csv`: RAG-style evidence retrieval examples for stakeholder questions.
- `outputs/real_embedding_status.json`: status for the optional real-embedding run.
- `outputs/evaluation_metrics.json`: confidence, cluster purity, and human-review metrics.
- `outputs/gold_label_evaluation.json`: labeled evaluation results for call type, theme, product, and risk routing.
- `outputs/gold_label_evaluation.csv`: per-example gold-label predictions and errors.
- `outputs/human_review_queue.csv`: low-confidence items that should be reviewed before automating workflow.
- `outputs/meeting_analysis.csv`: meeting-level detail for Q&A and drill-down.
- `outputs/dashboard.html`: simple browser dashboard for the demo walkthrough.

## Notes

The original assignment PDF is included as received. The dataset is unchanged; the pipeline only adds derived outputs under `outputs/`.
