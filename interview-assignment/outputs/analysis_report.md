# Transcript Intelligence Analysis

## Executive Takeaways

- The 100-call sample is best treated as a mixed operating signal, not just a transcript archive: customer support exposes acute defects, external customer calls expose renewal and adoption risk, and internal calls show how the organization prioritizes the work.
- Incident/reliability and compliance/audit conversations carry the highest operating risk. They combine negative sentiment, escalations, and many follow-up actions.
- Sentiment is most useful when read by call type. Customer support calls are predictably more negative, but external customer calls with only moderately negative language can be more commercially important because they connect product gaps to renewals, competitive evaluations, and trust.
- The highest-value product opportunity is a workflow that connects transcript themes to owner-ready next steps: product area, customer/account, evidence quote, risk level, and action item.

## Approach

I used a transparent hybrid pipeline rather than a black-box LLM pass. The provided summaries, topics, key moments, and utterance-level sentiment are used as semantic input. A rule-based scoring layer classifies each meeting into call type, primary theme, product surface, and risk score. I then added AI-system layers around that baseline: TF-IDF k-means clustering for unsupervised discovery, semantic retrieval for RAG-style evidence lookup, confidence scoring, a human-review queue, and a gold-label evaluation harness. The repo also includes an optional OpenAI embeddings path using `text-embedding-3-small`, an optional FastAPI review app, and unit tests for classifier/evaluation behavior.

## Theme Categories

| Theme | Meetings | Avg sentiment | Avg risk | Example transcripts |
|---|---:|---:|---:|---|
| Incident & Reliability | 24 | 2.23 | 10 | Detect Outage - Remediation Plan Review; Support Case #6977 - Brightpath Commerce Slow Backup Performance; Aegis / Meridian Capital - Service Reliability Discussion |
| Compliance & Audit | 22 | 4.37 | 7.59 | Aegis / Redwood Clinical - ISO 27001 Preparation; SOC 2 Audit Preparation - Internal; Comply v2 - Launch Readiness Review |
| Renewal & Commercial Risk | 17 | 3.64 | 8.53 | Support Case #9279 - Summit Trust Billing Inquiry; Aegis / Cobalt Software - Q2 Planning; Aegis / Atlas Precision - Contract Discussion |
| Identity & Access | 12 | 3.35 | 9.08 | Identity Team - Q2 Roadmap; Identity Team - Sprint Retro; Product Sync - Identity Roadmap |
| Product Feedback & Roadmap | 11 | 3.74 | 8.36 | Weekly Engineering Standup; Weekly Engineering Standup; Detect Team - Sprint Planning |
| Backup & Recovery | 8 | 3.99 | 9.12 | Support Case #1514 - Meridian Capital Granular Restore Request; Support Case #2638 - Pineridge Systems CloudPrime S3 Backup Connector; Aegis / Coastal Living Co - Protect Module Expansion |
| Competitive & Market | 6 | 2.82 | 10 | Competitive Threat Assessment - Post Outage; Win/Loss Analysis - Q1; Aegis / Brightpath Commerce - Competitive Evaluation |

## Sentiment by Call Type

| Call type | Meetings | Avg sentiment | Negative utterance share | Avg risk |
|---|---:|---:|---:|---:|
| Customer support | 31 | 2.8 | 27.1% | 8.9 |
| External customer | 39 | 3.9 | 9.5% | 8.59 |
| Internal | 30 | 3.42 | 16.9% | 9.17 |

## Meetings Worth Leadership Attention

- **Support Case #3266 - Trailhead Marketplace Detect Alerts Not Firing** (Customer support, Incident & Reliability): risk 10/10, sentiment 1.4. Isaac Brennan, infrastructure lead at Trailhead Marketplace, called Aegis Cloud Security support in frustration over a complete 15+ hour outage of Aegis Detect's event processing pipeline, leaving his retail platform blind to threats. Elena Vasquez and David K
- **URGENT: Blackridge Investments - Complete Loss of Threat Visibility** (Customer support, Incident & Reliability): risk 10/10, sentiment 1.6. Julia Tran from Blackridge Investments called Aegis Cloud Security support in a critical situation where her firm has had zero threat visibility for over three hours due to a known event processing pipeline failure. Marcus Williams confirmed the outage is a ca
- **Detect Outage - Customer Impact Assessment** (Internal, Incident & Reliability): risk 10/10, sentiment 1.8. The team convened an urgent internal call to address a significant outage of their Detect product that left customers without security monitoring for approximately six hours overnight. A single point of failure in the event ingestion pipeline caused a cascadin
- **Detect Outage - Escalation Bridge** (Internal, Incident & Reliability): risk 10/10, sentiment 1.8. A critical outage call was held between Tyler (engineering), Diana (customer success/sales), and Marcus (support) regarding a complete failure of the Detect threat monitoring pipeline that began at 2:47 AM. The ingestion layer experienced a cascading failure f
- **INCIDENT: Detect Pipeline Failure - War Room** (Internal, Incident & Reliability): risk 10/10, sentiment 1.8. A critical outage call was convened to address a complete failure of the Detect event processing pipeline that began around 9:14 AM Pacific. The ingestion pipeline's single primary node hit a memory ceiling and crashed due to lack of redundancy, a known tech d
- **URGENT: Cobalt Software - Aegis Detect Dashboard Down** (Customer support, Incident & Reliability): risk 10/10, sentiment 1.8. Lauren Bishop, VP of Infrastructure at Cobalt Software, called Aegis Cloud Security support reporting that their Aegis Detect dashboard was completely down with no threat visibility for nearly an hour. David Kim investigated and confirmed a platform-wide casca

## ML Discovery Experiment: TF-IDF Clusters

The clustering layer is not the production classifier; it is an exploratory check. It groups meetings by unsupervised text similarity, then compares each cluster to the hand-labeled business theme. This is useful for finding emerging pockets of language that rules might miss.

| Cluster | Meetings | Top terms | Dominant business theme | Avg risk |
|---:|---:|---|---|---:|
| 5 | 21 | pci, dss, pci dss, hipaa, soc, iso, comply, reporting | Compliance & Audit | 7.57 |
| 2 | 18 | failure, outage, pipeline, single, sprint, single point, point failure, ingestion | Incident & Reliability | 9.61 |
| 6 | 18 | renewal, pricing, comply, contract, backup, compliance, march, protect | Renewal & Commercial Risk | 8.28 |
| 0 | 13 | outage, post, incident, march, reliability, post incident, detect, nodes | Incident & Reliability | 9.77 |
| 1 | 13 | mfa, identity, sso, policy, okta, provisioning, scim, sync | Identity & Access | 9.15 |
| 4 | 13 | data, backup, platform, event, detect, failure, issue, outage | Incident & Reliability | 9.62 |
| 3 | 4 | control, feedback, gaps, role, pain, management, training, security training | Product Feedback & Roadmap | 8.5 |

## AI Evaluation and Human Review

To make the system more AI-ready, the pipeline now reports lightweight evaluation metrics and a review queue.

- Average theme confidence: **83%**
- Low-confidence meetings: **1** (1.0%)
- Average cluster purity against rule labels: **61%**

Human review queue:

- **Aegis / Meridian Capital - Service Reliability Discussion**: Incident & Reliability at 25% confidence, cluster `Outage`, risk 10/10

## Semantic Retrieval and Production AI Path

The repo includes two retrieval modes:

- **Local TF-IDF retrieval:** always runs and writes `semantic_search_examples.csv/json`.
- **Real embedding retrieval:** optional script `src/embedding_retrieval.py` calls OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set; otherwise it writes `real_embedding_status.json` with a skipped status.

This mirrors a production RAG pattern: embed transcript evidence, retrieve the most relevant calls for stakeholder questions, and constrain any future LLM-generated answer to cited transcript evidence.

The repo also includes:

- `src/app.py`: optional FastAPI review service with `/summary`, `/meetings`, `/search-examples`, and `/review-queue`.
- `tests/test_pipeline.py`: unit tests for call-type inference, theme priority, product routing, gold-label metrics, and vector similarity.


## Gold-Label Evaluation

I added a curated 20-meeting gold-label sample to evaluate the pipeline like an AI system, not just a dashboard.

- Call type accuracy: **100%**
- Theme accuracy: **100%**
- Product accuracy: **80%**
- Risk routing accuracy: **100%**
- High-risk detection F1: **100%**

This is deliberately small, but it establishes the evaluation harness. The production version should expand this into a labeled validation set with precision/recall by theme, reviewer agreement, and drift monitoring.


## Additional Insight Ideas

1. **Revenue risk heatmap for sales and CS leaders.** Combine renewal language, competitor mentions, negative sentiment, and account names to flag customers where product friction is turning into commercial risk.
2. **Product gap backlog generator for PMs.** Convert repeated pain points into ranked themes with direct quotes, affected accounts, current owner, and estimated urgency.
3. **Incident learning loop for engineering leads.** Link outage/support conversations to post-incident/internal planning calls to verify whether customer pain is making it into reliability work.
4. **Launch readiness monitor.** Track whether internal launch confidence aligns with customer-facing questions and support cases after GA.

## Limitations and Next Steps

- The classifier is intentionally explainable. The included TF-IDF clustering/retrieval is the local baseline; the optional embedding script shows the production path for semantic search, and an LLM labeling/extraction layer could be added on top while keeping the rule layer as guardrails and audit checks.
- Sentiment labels are sentence-level and do not distinguish politeness from business risk. The risk score corrects for this by incorporating escalations, action items, and negative operational terms.
- Account and owner extraction could be made more precise with named entity recognition or CRM enrichment.
- Product routing is the hardest current label because many calls mention several product surfaces; production should use utterance-level product attribution and reviewer-labeled training examples.
