# Transcript Intelligence Take-Home

This repository contains a complete, reproducible analysis of the provided transcript dataset for the Transcript Intelligence assessment.

## Deliverables

- Leadership slide deck: `deliverables/Transcript_Intelligence_Leadership_Deck.pptx`
- Technical pipeline and reference material:
  - `src/analyze_transcripts.py`
  - `src/build_deck.py`
  - `outputs/analysis_report.md`
  - `outputs/dashboard.html`
  - `outputs/meeting_analysis.csv`
  - `outputs/summary_metrics.json`
- Video demo support: `docs/video_demo_script.md`

## How to Run

From this folder:

```bash
python3 src/analyze_transcripts.py --dataset dataset --output outputs
NODE_PATH=/Users/srikaveri/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
  /Users/srikaveri/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  src/build_deck.js --outputs outputs --deliverables deliverables
```

The analysis pipeline has no required third-party Python dependencies. It uses the supplied JSON files directly. The slide deck is generated with `pptxgenjs` from the bundled Codex runtime so it opens cleanly in PowerPoint.

## Approach

I used a transparent hybrid approach:

1. Read each meeting folder and combine the transcript, summary, topics, key moments, and action items.
2. Classify each meeting by call type: customer support, external customer, or internal.
3. Score each meeting into one primary business theme and product surface using explainable keyword rules.
4. Aggregate utterance-level sentiment, provided meeting sentiment, action items, and risk signals.
5. Generate CSV/JSON outputs, an HTML dashboard, SVG charts, a written report, and a PowerPoint deck.

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
- `outputs/meeting_analysis.csv`: meeting-level detail for Q&A and drill-down.
- `outputs/dashboard.html`: simple browser dashboard for the demo walkthrough.

## Notes

The original assignment PDF is included as received. The dataset is unchanged; the pipeline only adds derived outputs under `outputs/` and `deliverables/`.
