#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const outputsDir = process.argv.includes("--outputs")
  ? process.argv[process.argv.indexOf("--outputs") + 1]
  : "outputs";
const deliverablesDir = process.argv.includes("--deliverables")
  ? process.argv[process.argv.indexOf("--deliverables") + 1]
  : "deliverables";

const summary = JSON.parse(fs.readFileSync(path.join(outputsDir, "summary_metrics.json"), "utf8"));
const clusterSummaryPath = path.join(outputsDir, "cluster_summary.json");
const clusterSummary = fs.existsSync(clusterSummaryPath)
  ? JSON.parse(fs.readFileSync(clusterSummaryPath, "utf8"))
  : [];
const evaluationPath = path.join(outputsDir, "evaluation_metrics.json");
const evaluation = fs.existsSync(evaluationPath)
  ? JSON.parse(fs.readFileSync(evaluationPath, "utf8"))
  : { avg_theme_confidence: 0, avg_cluster_purity: 0, low_confidence_meetings: 0, low_confidence_share: 0 };
const goldEvaluationPath = path.join(outputsDir, "gold_label_evaluation.json");
const goldEvaluation = fs.existsSync(goldEvaluationPath)
  ? JSON.parse(fs.readFileSync(goldEvaluationPath, "utf8"))
  : { call_type_accuracy: 0, theme_accuracy: 0, risk_accuracy: 0, high_risk_detection: { f1: 0 } };
fs.mkdirSync(deliverablesDir, { recursive: true });

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Srikaveri";
pptx.subject = "Transcript Intelligence Take-Home";
pptx.title = "Transcript Intelligence Leadership Deck";
pptx.company = "AegisCloud assessment";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.margin = 0;

const C = {
  ink: "182322",
  muted: "66716A",
  paper: "F6F2E9",
  wash: "EDE6D8",
  white: "FFFFFF",
  teal: "236A70",
  teal2: "7FA9A6",
  red: "A14C43",
  gold: "C18A2E",
  green: "4D7C5B",
  blue: "334E68",
  line: "D5CCBA",
  dark: "173230",
  charcoal: "243130",
};

function addBg(slide, color = C.paper) {
  slide.background = { color };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 0.18,
    h: 7.5,
    fill: { color: C.teal },
    line: { transparency: 100 },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.18,
    y: 0,
    w: 13.153,
    h: 0.16,
    fill: { color: C.wash },
    line: { transparency: 100 },
  });
}

function title(slide, text, kicker = "Transcript Intelligence") {
  slide.addShape(pptx.ShapeType.line, {
    x: 0.62,
    y: 1.55,
    w: 11.8,
    h: 0,
    line: { color: C.line, width: 1 },
  });
  slide.addText(kicker.toUpperCase(), {
    x: 0.62,
    y: 0.35,
    w: 5.2,
    h: 0.28,
    fontFace: "Aptos",
    fontSize: 8.5,
    bold: true,
    color: C.teal,
    breakLine: false,
    charSpace: 1.2,
  });
  slide.addText(text, {
    x: 0.62,
    y: 0.74,
    w: 11.8,
    h: 0.68,
    fontFace: "Aptos Display",
    fontSize: 25,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
}

function footer(slide) {
  slide.addShape(pptx.ShapeType.line, {
    x: 0.62,
    y: 6.92,
    w: 11.95,
    h: 0,
    line: { color: C.line, width: 0.75, transparency: 25 },
  });
  slide.addText("100 transcript folders | explainable pipeline | retrieval + evaluation layer", {
    x: 0.62,
    y: 7.08,
    w: 7.5,
    h: 0.18,
    fontSize: 7,
    color: C.muted,
    margin: 0,
  });
}

function rect(slide, x, y, w, h, fill, line = fill, radius = 0.08) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: radius,
    fill: { color: fill },
    line: { color: line, transparency: line === fill ? 100 : 0, width: 1 },
  });
}

function line(slide, x, y, w, color = C.line, width = 1) {
  slide.addShape(pptx.ShapeType.line, {
    x,
    y,
    w,
    h: 0,
    line: { color, width },
  });
}

function card(slide, label, value, note, x, y, color = C.teal) {
  rect(slide, x, y, 3.65, 1.2, C.white, C.line);
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 3.65,
    h: 0.08,
    fill: { color },
    line: { transparency: 100 },
  });
  slide.addText(label.toUpperCase(), { x: x + 0.24, y: y + 0.2, w: 2.95, h: 0.16, fontSize: 7.5, bold: true, color: C.muted, margin: 0, fit: "shrink", charSpace: 1 });
  slide.addText(value, { x: x + 0.24, y: y + 0.42, w: 1.35, h: 0.4, fontSize: 25, bold: true, color, margin: 0, fit: "shrink" });
  slide.addText(note, { x: x + 1.55, y: y + 0.43, w: 1.78, h: 0.48, fontSize: 10.4, color: C.ink, margin: 0.02, fit: "shrink" });
}

function pill(slide, text, x, y, w, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.34,
    rectRadius: 0.06,
    fill: { color, transparency: 5 },
    line: { color, transparency: 100 },
  });
  slide.addText(text.toUpperCase(), { x: x + 0.1, y: y + 0.095, w: w - 0.2, h: 0.15, fontSize: 7.5, bold: true, color: C.white, align: "center", margin: 0, fit: "shrink", charSpace: 0.8 });
}

function bullets(slide, items, x, y, w, h, fontSize = 17) {
  slide.addText(
    items.map((t) => ({ text: t, options: { bullet: { type: "ul" }, hanging: 4 } })),
    { x, y, w, h, fontSize, color: C.ink, breakLine: false, margin: 0.04, fit: "shrink", paraSpaceAfterPt: 9 }
  );
}

function barChart(slide, items, x, y, w, h, color, suffix = "") {
  const max = Math.max(...items.map(([, v]) => v), 1);
  const rowH = h / items.length;
  items.forEach(([label, value], i) => {
    const yy = y + i * rowH;
    const barW = Math.max(0.05, (value / max) * (w - 2.75));
    slide.addText(label, { x, y: yy + 0.02, w: 2.45, h: 0.25, fontSize: 9.2, color: C.charcoal, margin: 0, fit: "shrink" });
    rect(slide, x + 2.58, yy + 0.05, w - 3.0, 0.18, "E3DBCD", "E3DBCD", 0.04);
    rect(slide, x + 2.58, yy + 0.05, barW, 0.18, color, color, 0.04);
    slide.addText(`${value}${suffix}`, { x: x + 2.72 + Math.min(barW, w - 3.55), y: yy + 0.045, w: 0.65, h: 0.18, fontSize: 8.4, bold: true, color: C.ink, margin: 0, fit: "shrink" });
  });
}

function note(slide, heading, text, x, y, w, h) {
  rect(slide, x, y, w, h, C.white, C.line);
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.08,
    h,
    fill: { color: C.teal },
    line: { transparency: 100 },
  });
  slide.addText(heading, { x: x + 0.28, y: y + 0.24, w: w - 0.55, h: 0.26, fontSize: 13.5, bold: true, color: C.teal, margin: 0 });
  slide.addText(text, { x: x + 0.28, y: y + 0.68, w: w - 0.55, h: h - 0.86, fontSize: 14.5, color: C.ink, margin: 0.02, fit: "shrink", breakLine: false });
}

function chapter(slide, n, label, x = 11.5, y = 0.36) {
  slide.addText(String(n).padStart(2, "0"), { x, y, w: 0.48, h: 0.2, fontSize: 8, bold: true, color: C.teal, margin: 0, align: "right" });
  slide.addText(label.toUpperCase(), { x: x + 0.6, y, w: 0.95, h: 0.2, fontSize: 7, bold: true, color: C.muted, margin: 0, fit: "shrink", charSpace: 0.8 });
}

function getType(name) {
  return summary.call_type_summary.find((x) => x.call_type === name);
}

// Slide 1
{
  const s = pptx.addSlide();
  s.background = { color: C.dark };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: C.gold }, line: { transparency: 100 } });
  s.addShape(pptx.ShapeType.rect, { x: 9.1, y: 0, w: 4.25, h: 7.5, fill: { color: "234542", transparency: 0 }, line: { transparency: 100 } });
  s.addShape(pptx.ShapeType.arc, { x: 8.35, y: 0.4, w: 4.1, h: 4.1, line: { color: C.teal2, transparency: 35, width: 2 }, adjustPoint: 0.45 });
  s.addShape(pptx.ShapeType.arc, { x: 9.15, y: 1.25, w: 3.15, h: 3.15, line: { color: C.gold, transparency: 20, width: 2 }, adjustPoint: 0.65 });
  s.addText("Transcript\nIntelligence", { x: 0.72, y: 0.75, w: 6.8, h: 1.45, fontFace: "Aptos Display", fontSize: 42, bold: true, color: C.white, margin: 0, breakLine: false, fit: "shrink" });
  s.addText("A leadership-ready AI analysis of 100 enterprise call transcripts", { x: 0.76, y: 2.42, w: 6.8, h: 0.42, fontSize: 18, color: "DCE9E5", margin: 0, fit: "shrink" });
  pill(s, "Explainable baseline", 0.76, 3.15, 1.85, C.teal);
  pill(s, "Retrieval + evaluation", 2.8, 3.15, 2.1, C.gold);
  pill(s, "Production path", 5.08, 3.15, 1.6, C.green);
  card(s, "meetings", "100", "Support, external customer, and internal calls.", 0.76, 5.15, C.teal2);
  card(s, "themes", "7", "Business-oriented routing taxonomy.", 4.25, 5.15, C.gold);
  s.addText("Senior AI Engineer take-home", { x: 9.55, y: 5.85, w: 2.8, h: 0.28, fontSize: 11, bold: true, color: C.white, margin: 0 });
  s.addText("Pipeline | RAG-style retrieval | gold-label eval | FastAPI review app", { x: 9.55, y: 6.18, w: 2.8, h: 0.48, fontSize: 10, color: "DCE9E5", margin: 0, fit: "shrink" });
}

// Slide 2
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 1, "Corpus");
  title(s, "The transcript corpus is an operating signal, not just meeting notes");
  bullets(s, [
    "Support calls reveal acute pain: outages, latency, connector bugs, billing disputes.",
    "External customer calls reveal commercial risk: renewals, trust, competitive evaluations, roadmap confidence.",
    "Internal calls reveal whether the organization is closing the loop on customer pain.",
  ], 0.8, 1.82, 6.2, 2.0, 18);
  card(s, "Customer support", String(getType("Customer support").meetings), "Highest negative utterance share.", 7.4, 1.7, C.red);
  card(s, "External customer", String(getType("External customer").meetings), "Lower sentiment risk, higher revenue context.", 7.4, 3.05, C.teal);
  card(s, "Internal", String(getType("Internal").meetings), "Prioritization and execution signal.", 7.4, 4.4, C.gold);
  footer(s);
}

// Slide 3
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 2, "Pipeline");
  title(s, "A transparent hybrid classifier is the right first system");
  note(s, "Pipeline", "Raw JSON folders -> summaries/topics/key moments -> rule-scored call type, theme, product surface, sentiment, risk -> CSV/JSON/HTML/deck outputs", 0.7, 1.68, 5.7, 1.45);
  bullets(s, [
    "Explainable enough for product and engineering Q&A.",
    "Repeatable with no external services or API keys.",
    "Easy to replace theme rules with embeddings or LLM labels later while keeping audit guardrails.",
  ], 0.7, 3.68, 5.9, 1.7, 16);
  rect(s, 7.0, 1.72, 4.7, 3.7, C.white, C.line);
  s.addText("Core outputs", { x: 7.35, y: 2.02, w: 2.4, h: 0.32, fontSize: 18, bold: true, color: C.ink, margin: 0 });
  s.addText("meeting_analysis.csv\nsummary_metrics.json\nanalysis_report.md\ndashboard.html\nTranscript_Intelligence_Leadership_Deck.pptx", { x: 7.35, y: 2.55, w: 3.9, h: 1.8, fontSize: 15, color: C.ink, margin: 0, fit: "shrink" });
  footer(s);
}

// Slide 4
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 3, "Themes");
  title(s, "Reliability is the largest high-risk signal; compliance is broad but healthier");
  barChart(s, summary.theme_summary.map((x) => [x.theme, x.meetings]), 0.72, 1.65, 7.2, 4.7, C.teal);
  note(s, "Interpretation", "Incident & Reliability reaches the risk ceiling because it combines urgent language, customer impact, and technical follow-up. Compliance is frequent, but many conversations are planned reviews or launch/adoption work.", 8.35, 1.8, 3.65, 2.4);
  footer(s);
}

// Slide 5
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 4, "Sentiment");
  title(s, "Sentiment trends separate acute support pain from commercial risk");
  barChart(s, summary.call_type_summary.map((x) => [x.call_type, Number((x.negative_utterance_share * 100).toFixed(1))]), 0.75, 1.65, 6.8, 2.4, C.red, "%");
  barChart(s, summary.call_type_summary.map((x) => [x.call_type, x.avg_sentiment_score]), 0.75, 4.45, 6.8, 1.7, C.green);
  note(s, "What it means", "Support calls are the emotional smoke alarm: 27.1% of utterances are negative. External customer calls sound calmer, but risk often sits in renewal hesitation, competitive evaluation, and roadmap confidence. Both signals need different owners.", 8.2, 1.8, 3.8, 2.5);
  footer(s);
}

// Slide 6
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 5, "Product");
  title(s, "Product risk concentrates around Detect, then Protect and Identity");
  barChart(s, summary.product_summary.map((x) => [x.product, x.avg_risk_score]), 0.85, 1.75, 6.6, 3.1, C.gold);
  note(s, "Recommendation", "Use transcript intelligence as a product risk router: extract the affected product, evidence quote, account, sentiment, and action owner. Detect should be the first executive dashboard surface because outages, SIEM connectors, alert quality, and competitive gaps recur across call types.", 8.0, 1.85, 3.8, 2.7);
  footer(s);
}

// Slide 7
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 6, "Risk");
  title(s, "Highest-risk meetings show the decisions leaders should force");
  const headers = [["Meeting", 0.72, 5.2], ["Theme", 6.15, 2.0], ["Risk", 8.35, 0.8], ["Leadership question", 9.35, 2.8]];
  headers.forEach(([t, x, w]) => s.addText(t, { x, y: 1.62, w, h: 0.25, fontSize: 10, bold: true, color: C.muted, margin: 0 }));
  summary.highest_risk_meetings.slice(0, 6).forEach((item, i) => {
    const y = 1.95 + i * 0.72;
    rect(s, 0.65, y, 11.7, 0.55, C.white, C.line);
    s.addText(item.title.slice(0, 62), { x: 0.82, y: y + 0.15, w: 5.0, h: 0.2, fontSize: 9.5, color: C.ink, margin: 0, fit: "shrink" });
    s.addText(item.theme, { x: 6.15, y: y + 0.15, w: 1.9, h: 0.2, fontSize: 9.5, color: C.ink, margin: 0, fit: "shrink" });
    s.addText(String(item.risk_score), { x: 8.45, y: y + 0.15, w: 0.4, h: 0.2, fontSize: 11, bold: true, color: C.red, margin: 0 });
    s.addText("Owner, tradeoff, customer impact", { x: 9.35, y: y + 0.15, w: 2.7, h: 0.2, fontSize: 9.5, color: C.ink, margin: 0, fit: "shrink" });
  });
  footer(s);
}

// Slide 8
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 7, "Discovery");
  title(s, "A lightweight clustering experiment validates and challenges the taxonomy");
  barChart(s, clusterSummary.map((x) => [`C${x.cluster_id}: ${x.cluster_label}`, x.meetings]), 0.75, 1.65, 6.9, 4.3, C.green);
  note(s, "What the experiment adds", "The pipeline includes a dependency-free TF-IDF k-means pass. It is not the production classifier; it is a discovery check that groups similar meetings and compares each cluster with the hand-labeled business theme. The result gives reviewers evidence that the taxonomy was tested, not only asserted.", 8.15, 1.75, 3.8, 2.9);
  footer(s);
}

// Slide 9
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 8, "AI Layer");
  title(s, "The AI layer includes retrieval, confidence, and human review");
  card(s, "Theme confidence", `${Math.round(evaluation.avg_theme_confidence * 100)}%`, "Average confidence across the rule-labeled taxonomy.", 0.75, 1.65, C.teal);
  card(s, "Cluster purity", `${Math.round(evaluation.avg_cluster_purity * 100)}%`, "How often unsupervised clusters align with dominant business labels.", 4.85, 1.65, C.green);
  card(s, "Review queue", String(evaluation.low_confidence_meetings), "Low-confidence meetings routed for human review before automation.", 8.95, 1.65, C.gold);
  note(s, "Production AI path", "The current repo uses dependency-free TF-IDF retrieval as a RAG-style prototype. In production, I would replace this with embedding search, LLM extraction constrained to retrieved transcript evidence, confidence thresholds, and human review for ambiguous or high-risk account conversations.", 1.0, 3.55, 10.9, 2.0);
  footer(s);
}

// Slide 10
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 9, "Eval");
  title(s, "A gold-label harness turns this from analysis into an AI system");
  card(s, "Call type", `${Math.round(goldEvaluation.call_type_accuracy * 100)}%`, "Accuracy on the curated validation slice.", 0.75, 1.65, C.teal);
  card(s, "Theme", `${Math.round(goldEvaluation.theme_accuracy * 100)}%`, "Accuracy on primary business taxonomy labels.", 4.85, 1.65, C.green);
  card(s, "Risk F1", `${Math.round(goldEvaluation.high_risk_detection.f1 * 100)}%`, "High-risk detection precision/recall balance.", 8.95, 1.65, C.gold);
  note(s, "Why this matters", "A senior AI system should not stop at generated charts. The repo now includes a 20-meeting gold-label sample and reports accuracy plus precision/recall/F1. In production, this expands into a stratified validation set, reviewer agreement, regression tests, and drift monitoring.", 1.0, 3.55, 10.9, 2.0);
  footer(s);
}

// Slide 11
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 10, "Platform");
  title(s, "Production extensions: real embeddings, API service, and tests");
  card(s, "Embeddings", "OpenAI", "Optional real retrieval via text-embedding-3-small when OPENAI_API_KEY is set.", 0.75, 1.65, C.teal);
  card(s, "API", "FastAPI", "Review endpoints for summary, meetings, retrieval examples, and human-review queue.", 4.85, 1.65, C.green);
  card(s, "Tests", "6", "Unit coverage for classifier, routing, gold eval, and vector similarity behavior.", 8.95, 1.65, C.gold);
  note(s, "Why this matters", "The repo remains easy to run locally, but the architecture now has clear production interfaces: swap TF-IDF retrieval for embeddings, expose review workflows through an API, and protect behavior with tests and gold-label regression checks.", 1.0, 3.55, 10.9, 2.0);
  footer(s);
}

// Slide 12
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 11, "Products");
  title(s, "Three insight products would make this valuable beyond analysis");
  card(s, "Sales / CS", "1", "Revenue risk heatmap: renewal language + competitor mentions + negative sentiment.", 0.75, 1.8, C.teal);
  card(s, "Product", "2", "Product gap backlog: repeated pain points with quotes, accounts, and urgency.", 4.85, 1.8, C.gold);
  card(s, "Engineering", "3", "Incident learning loop: connect support pain to post-incident and sprint-planning follow-through.", 8.95, 1.8, C.green);
  s.addText("These are stakeholder workflows, not charts. The product should help each leader decide what to do next and where to look for evidence.", {
    x: 1.0,
    y: 4.2,
    w: 10.8,
    h: 0.9,
    fontSize: 22,
    bold: true,
    color: C.ink,
    align: "center",
    margin: 0,
    fit: "shrink",
  });
  footer(s);
}

// Slide 13
{
  const s = pptx.addSlide();
  addBg(s);
  chapter(s, 12, "Next");
  title(s, "Recommended next build");
  bullets(s, [
    "Ship a theme and risk dashboard for Detect reliability first.",
    "Add account-level revenue risk overlays for renewal and competitive calls.",
    "Add owner extraction so action items become trackable workflow, not static notes.",
    "Upgrade classifier with embeddings or LLM labels, keeping the rule layer as explainable QA.",
  ], 0.9, 1.85, 6.4, 2.4, 18);
  rect(s, 8.0, 1.8, 3.6, 3.4, C.white, C.line);
  s.addText("Demo path", { x: 8.35, y: 2.1, w: 2.2, h: 0.3, fontSize: 18, bold: true, color: C.ink, margin: 0 });
  s.addText("1. Run src/analyze_transcripts.py\n2. Open outputs/dashboard.html\n3. Review analysis_report.md\n4. Walk through this deck\n5. Show highest-risk CSV rows", {
    x: 8.35,
    y: 2.65,
    w: 2.8,
    h: 1.7,
    fontSize: 15,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  footer(s);
}

pptx.writeFile({ fileName: path.join(deliverablesDir, "Transcript_Intelligence_Leadership_Deck.pptx") });
