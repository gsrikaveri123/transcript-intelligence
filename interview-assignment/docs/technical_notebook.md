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
- `cluster_id`, `cluster_terms`, `cluster_label`: lightweight TF-IDF k-means discovery output.
- `theme_confidence`: confidence score used to route ambiguous meetings to human review.

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

## ML Experimentation

The pipeline includes a dependency-free TF-IDF k-means clustering experiment. This is intentionally positioned as discovery, not the source of truth. It groups meetings by text similarity using titles, topics, summaries, and evidence quotes, then reports top terms and the dominant hand-labeled theme for each cluster.

The value of this section is twofold:

- It shows whether unsupervised language patterns broadly support the chosen taxonomy.
- It reveals pockets of language that a purely rule-based classifier might miss or over-generalize.

See:

- `outputs/cluster_summary.csv`
- `outputs/cluster_summary.json`
- `outputs/cluster_counts.svg`

## Semantic Retrieval and RAG Pattern

The pipeline also includes a lightweight semantic retrieval layer. It indexes the meetings with the same TF-IDF representation and runs stakeholder-oriented questions against the corpus, returning the most relevant transcripts with evidence quotes.

Example questions:

- Which calls show Detect reliability or outage risk?
- Where do customers mention renewal risk, pricing, or competitive evaluation?
- What product gaps should product managers prioritize?
- Which compliance or audit conversations need roadmap follow-up?

See:

- `outputs/semantic_search_examples.csv`
- `outputs/semantic_search_examples.json`

In production, this would become a RAG workflow using embeddings, vector search, source citations, and LLM-generated summaries constrained to retrieved evidence.

## Evaluation and Human Review

The current repo includes lightweight AI evaluation artifacts:

- Average taxonomy confidence.
- Cluster purity versus the rule-based labels.
- A low-confidence human-review queue.

This matters because a transcript intelligence product should not automatically route ambiguous customer conversations without review. The confidence and review queue show how I would design a human-in-the-loop path before production automation.

See:

- `outputs/evaluation_metrics.json`
- `outputs/human_review_queue.csv`

## Production Next Steps

- Add embedding clustering to discover emerging topics not covered by the current taxonomy.
- Replace TF-IDF retrieval with embedding search and cite retrieved utterances in LLM-generated answers.
- Add a labeled evaluation set and measure precision/recall for themes, action-item extraction, risk detection, and owner routing.
- Add an LLM labeling pass with confidence scores and explanation snippets.
- Add entity extraction for account, competitor, product module, owner, and severity.
- Connect output to CRM, ticketing, and roadmap systems so insight becomes workflow.
