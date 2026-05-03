# 5-10 Minute Video Demo Script

## 0:00-0:45 — Context

"This is my Transcript Intelligence assessment. The goal was to process 100 call transcripts, categorize them by theme, analyze sentiment across call types, and identify additional insights useful to product and engineering leaders."

Show:

- `README.md`
- `dataset/`
- `src/`
- `outputs/`
- `deliverables/`

## 0:45-2:15 — Run the Pipeline

Run:

```bash
python3 src/analyze_transcripts.py --dataset dataset --output outputs
```

Narration:

"The pipeline is deliberately explainable. It reads each meeting folder, combines the summary, topics, key moments, action items, and utterance-level sentiment, then assigns call type, primary theme, product surface, and risk score. I chose this hybrid rule-based approach because it is easy to inspect during Q&A and can later be upgraded with embeddings or LLM labels."

Show:

- `outputs/meeting_analysis.csv`
- `outputs/summary_metrics.json`

## 2:15-4:00 — Walk Through the Findings

Open:

```bash
open outputs/dashboard.html
```

Narration:

"The most important finding is that reliability is the highest-risk theme. It does not just show up in support tickets; it also appears in customer impact calls, post-incident reviews, and competitive discussions. Compliance is frequent, but many compliance calls are healthier planned reviews or launch conversations."

Show:

- Theme volume
- TF-IDF cluster summary
- Highest-risk meeting table
- `outputs/call_type_summary.csv`

Call out:

- Customer support has the highest negative utterance share.
- External customer calls sound calmer but can carry renewal and competitive risk.
- Internal calls show whether the organization is actually closing the loop.

## 4:00-6:00 — Slide Deck Walkthrough

Open:

- `deliverables/Transcript_Intelligence_Leadership_Deck.pptx`

Narration:

"The deck is designed for a product and engineering leadership audience, so it leads with decisions and implications rather than code. The recommendation is to treat Transcript Intelligence as a routing layer: connect the call, product surface, account, risk level, quote evidence, and action owner."

Recommended slides to emphasize:

- Corpus as an operating signal
- Hybrid classifier approach
- Reliability and sentiment trends
- Product risk routing
- Additional insight products

## 6:00-8:00 — Technical Q&A Readiness

Show:

- `src/analyze_transcripts.py`
- `classify_call_type`
- `top_two_theme`
- `sentiment_from_transcript`
- `risk_score`
- `add_discovery_clusters`

Narration:

"The important technical decision is transparency. I wanted a pipeline where every label can be explained. If a stakeholder challenges a category, we can inspect the source text and the rule. I also added a lightweight TF-IDF k-means clustering experiment to show discovery beyond hand-written rules. In production, I would replace that with embeddings or LLM labeling and measure agreement against this explainable baseline."

## 8:00-9:30 — Close

"The biggest product opportunity is to turn transcripts into stakeholder-specific workflows: revenue risk heatmaps for GTM leaders, product gap backlog generation for PMs, and incident learning loops for engineering. The current repository demonstrates the foundation, and the next step would be richer entity extraction and CRM or ticketing enrichment."
