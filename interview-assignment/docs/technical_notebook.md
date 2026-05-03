# Technical Notebook

## Question

How can a B2B SaaS company turn call transcripts into usable product, engineering, support, and GTM intelligence?

## Dataset

The dataset contains 100 meeting folders. Each folder includes:

- `meeting-info.json`: title, participants, timestamps, duration.
- `transcript.json`: utterance-level transcript with speaker and sentiment labels.
- `summary.json`: summary, action items, topics, overall sentiment score, and key moments.
- `speakers.json`, `events.json`, `speaker-meta.json`: supporting metadata.

## Modeling Decision

I chose a transparent hybrid pipeline instead of a fully black-box LLM workflow.

Reasons:

- The assessment asks to show reasoning, not just output.
- The provided summaries/topics/key moments already contain useful semantic compression.
- Rule-based labels are easy to inspect in live Q&A.
- The approach can be upgraded later with embeddings or LLM labels while preserving explainable audit rules.

## Features Generated

For each meeting, the pipeline creates:

- `call_type`: customer support, external customer, or internal.
- `primary_theme`: one of seven business-oriented categories.
- `products`: product surfaces mentioned strongly enough to matter.
- `sentiment_score`: provided meeting-level sentiment.
- `transcript_sentiment_score`: aggregate from utterance-level labels.
- `negative_utterance_share` and `positive_utterance_share`.
- `risk_score`: 0-10 heuristic combining escalation language, negative utterances, and action-item load.
- `example_quote`: evidence quote selected from the transcript.

## Theme Taxonomy

The categories are intentionally stakeholder-readable:

- Incident & Reliability
- Compliance & Audit
- Renewal & Commercial Risk
- Product Feedback & Roadmap
- Backup & Recovery
- Identity & Access
- Competitive & Market

## Main Results

See:

- `outputs/theme_summary.csv`
- `outputs/call_type_summary.csv`
- `outputs/product_summary.csv`
- `outputs/analysis_report.md`

The strongest pattern is that reliability is the highest-risk theme even when it is not the largest theme. It shows up across support tickets, customer impact calls, internal post-incident work, and competitive conversations.

## Production Next Steps

- Add embedding clustering to discover emerging topics not covered by the current taxonomy.
- Add an LLM labeling pass with confidence scores and explanation snippets.
- Add entity extraction for account, competitor, product module, owner, and severity.
- Connect output to CRM, ticketing, and roadmap systems so insight becomes workflow.
