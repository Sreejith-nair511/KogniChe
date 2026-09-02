# Submission Package — NEXORA
## APS-04 · Kognivera Hackathon 2026

This folder contains all source documents for the NEXORA design submission.  
Compile them into one PDF using the instructions below.

---

## File Index

| File | Contents | Pages (est.) |
|------|----------|-------------|
| `00_COVER.md` | Cover page, positioning statement, implementation status table | 1 |
| `01_EXECUTIVE_SUMMARY.md` | Problem, solution, real metrics overview | 1 |
| `02_PROBLEM_UNDERSTANDING.md` | Five failure modes of traditional search; NEXORA's reframing | 1 |
| `03_SCOPE_AND_NON_SCOPE.md` | MVP in/out table; rationale for scope decisions | 1 |
| `04_USER_JOURNEY.md` | Human journey (Arjun's story) + technical step-by-step flow | 2 |
| `05_SOLUTION_OVERVIEW.md` | Pipeline table, differentiators, novelty | 1 |
| `06_ARCHITECTURE.md` | 9-layer architecture, dependency map, module reference | 2 |
| `07_SYSTEM_FLOW.md` | Search flow stage-by-stage + feedback loop + telemetry | 2 |
| `08_AI_FEATURES_AND_GROUNDING.md` | Feature inventory table, grounding principle, cold-start contract | 2 |
| `09_HYBRID_RETRIEVAL.md` | SQL hard filter design, semantic retrieval, candidate fusion | 2 |
| `10_PERSONALIZATION_AND_RERANKING.md` | Profile construction, maturity model, reranking formula, MMR | 2 |
| `11_COLD_START_AND_SESSION_LEARNING.md` | Cold-start contract, session profile, feedback loop | 2 |
| `12_MULTILINGUAL_INTELLIGENCE.md` | Language support, cross-lingual retrieval, verified test | 1 |
| `13_EXPLAINABILITY.md` | Why This, Why Now, confidence, DNA, explainability contract | 2 |
| `14_DATASET_AND_DATA_USAGE.md` | Table reference, data rules observed, limitations | 2 |
| `15_EVALUATION_STRATEGY.md` | Metrics, real results, model comparison, honest analysis | 2 |
| `16_BUSINESS_BENEFITS.md` | Traveller value, platform value, honest claims | 1 |
| `17_TECH_STACK.md` | Full stack table, architecture decisions, infrastructure | 2 |
| `18_24_HOUR_EXECUTION_PLAN.md` | Hour-by-hour plan + actual status | 2 |
| `19_RISKS_AND_FALLBACKS.md` | Risk table with mitigations + degradation hierarchy | 1 |
| `20_MVP_ACCEPTANCE_CRITERIA.md` | Full checklist with ✅/⚠️/🔲 status | 2 |
| `21_FINAL_DEMO_FLOW.md` | 9-step demo script with exact actions and messages | 2 |
| `22_CONCLUSION.md` | Summary, evidence table, closing statement | 1 |

**Estimated total: 37 pages** (will compress to 18–25 in PDF with section-break styling)

---

## Diagram Files

| File | Format | Description |
|------|--------|-------------|
| `assets/diagrams/architecture.mmd` | Mermaid | Full system architecture flowchart |
| `assets/diagrams/system_flow.mmd` | Mermaid | Search + feedback loop flow |

### Rendering Diagrams

**Option 1 — Mermaid CLI (recommended)**
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i assets/diagrams/architecture.mmd -o assets/diagrams/architecture.png -t dark -b transparent -w 1400
mmdc -i assets/diagrams/system_flow.mmd  -o assets/diagrams/system_flow.png  -t dark -b transparent -w 1200
```

**Option 2 — VS Code**
Install the "Mermaid Preview" extension. Open any `.mmd` file and preview in split pane.

**Option 3 — Online**
Paste contents of any `.mmd` file into https://mermaid.live for instant rendering.

---

## Compiling to PDF

### Method 1 — Pandoc (preferred, professional output)

```bash
# Install Pandoc + a LaTeX engine (or use the HTML route)
pip install pandoc

# Single-command compile (all sections in order)
pandoc \
  00_COVER.md \
  01_EXECUTIVE_SUMMARY.md \
  02_PROBLEM_UNDERSTANDING.md \
  03_SCOPE_AND_NON_SCOPE.md \
  04_USER_JOURNEY.md \
  05_SOLUTION_OVERVIEW.md \
  06_ARCHITECTURE.md \
  07_SYSTEM_FLOW.md \
  08_AI_FEATURES_AND_GROUNDING.md \
  09_HYBRID_RETRIEVAL.md \
  10_PERSONALIZATION_AND_RERANKING.md \
  11_COLD_START_AND_SESSION_LEARNING.md \
  12_MULTILINGUAL_INTELLIGENCE.md \
  13_EXPLAINABILITY.md \
  14_DATASET_AND_DATA_USAGE.md \
  15_EVALUATION_STRATEGY.md \
  16_BUSINESS_BENEFITS.md \
  17_TECH_STACK.md \
  18_24_HOUR_EXECUTION_PLAN.md \
  19_RISKS_AND_FALLBACKS.md \
  20_MVP_ACCEPTANCE_CRITERIA.md \
  21_FINAL_DEMO_FLOW.md \
  22_CONCLUSION.md \
  -o ../NEXORA_Design_Submission_APS04.pdf \
  --pdf-engine=wkhtmltopdf \
  --metadata title="NEXORA — APS-04 Design Submission" \
  --toc \
  --toc-depth=2 \
  --css=assets/style.css \
  -V margin-top=20mm \
  -V margin-bottom=20mm \
  -V margin-left=22mm \
  -V margin-right=22mm
```

### Method 2 — VS Code + Markdown PDF Extension

1. Install extension: `yzane.markdown-pdf`
2. Open `00_COVER.md`
3. Right-click → "Markdown PDF: Export (pdf)"
4. Repeat for each file, then merge with a PDF merger tool
5. Or: concatenate all `.md` files first → export as one

```bash
# Windows PowerShell — concatenate in order
Get-Content 00_COVER.md, 01_EXECUTIVE_SUMMARY.md, 02_PROBLEM_UNDERSTANDING.md, `
  03_SCOPE_AND_NON_SCOPE.md, 04_USER_JOURNEY.md, 05_SOLUTION_OVERVIEW.md, `
  06_ARCHITECTURE.md, 07_SYSTEM_FLOW.md, 08_AI_FEATURES_AND_GROUNDING.md, `
  09_HYBRID_RETRIEVAL.md, 10_PERSONALIZATION_AND_RERANKING.md, `
  11_COLD_START_AND_SESSION_LEARNING.md, 12_MULTILINGUAL_INTELLIGENCE.md, `
  13_EXPLAINABILITY.md, 14_DATASET_AND_DATA_USAGE.md, `
  15_EVALUATION_STRATEGY.md, 16_BUSINESS_BENEFITS.md, `
  17_TECH_STACK.md, 18_24_HOUR_EXECUTION_PLAN.md, `
  19_RISKS_AND_FALLBACKS.md, 20_MVP_ACCEPTANCE_CRITERIA.md, `
  21_FINAL_DEMO_FLOW.md, 22_CONCLUSION.md `
  | Set-Content NEXORA_combined.md
```

Then export `NEXORA_combined.md` as PDF.

### Method 3 — Python script (automated, included)

```bash
python compile_submission.py
```

See `compile_submission.py` in this folder. Requires `markdown`, `weasyprint` or `pdfkit`.

---

## Verifying the Final PDF

Before submitting:
- [ ] File name: `NEXORA_APS-04_Design_Submission.pdf`
- [ ] File size: under 25 MB
- [ ] All 22 sections present
- [ ] Diagrams rendered (not showing as raw Mermaid text)
- [ ] Tables display correctly
- [ ] No `[truncated]` or `[TODO]` markers
- [ ] Real metrics in Section 15 (P@5=0.2900, NDCG@10=0.2988, etc.)
- [ ] Open in a fresh PDF viewer to confirm rendering

---

## Assets Summary

```
assets/
  diagrams/
    architecture.mmd      Full system architecture (Mermaid)
    system_flow.mmd       Search flow + feedback loop (Mermaid)
  tables/
    dataset_summary.md    APS-04 dataset reference tables
    evaluation_results.md Real metric results + comparison
```
