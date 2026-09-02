# Submission Checklist — NEXORA APS-04

Mark each item before uploading. Do not submit until all required items are checked.

---

## Document Completeness

- [x] Problem understanding (Section 02) — original words, not copied from brief
- [x] Scope — explicit IN and OUT lists (Section 03)
- [x] User journey — human narrative + technical flow (Section 04)
- [x] Architecture diagram — Mermaid flowchart showing all layers (Section 06 + assets/diagrams/)
- [x] System flow diagram — search pipeline + feedback loop (Section 07 + assets/diagrams/)
- [x] AI features — feature × input × method × output × grounding × business value (Section 08)
- [x] AI grounding — every recommendation traceable to APS-04 data (Section 08)
- [x] Hybrid retrieval — hard filter design + semantic retrieval + fusion (Section 09)
- [x] Personalization — profile construction, maturity model, reranking formula (Section 10)
- [x] Cold-start handling — 600 cold-start users addressed (Section 11)
- [x] Session learning — short-term vs long-term intent, signal weights (Section 11)
- [x] Multilingual intelligence — en-IN, hi, ta, ml + cross-lingual retrieval (Section 12)
- [x] Explainability — Why This, Why Now, confidence, DNA (Section 13)
- [x] Dataset usage — all 15 tables documented with field-level detail (Section 14)
- [x] Evaluation methodology — Precision@K, NDCG@K, Recall@K, MRR (Section 15)
- [x] Business benefits — traveller value + platform value, no fake ROI (Section 16)
- [x] Tech stack — complete table with rationale (Section 17)
- [x] 24-hour execution plan — hour-by-hour, with actual status (Section 18)
- [x] Risks and fallbacks — risk table + degradation hierarchy (Section 19)
- [x] MVP acceptance criteria — full checklist with status (Section 20)
- [x] Final demo flow — 9-step scripted demo (Section 21)
- [x] Conclusion — concise, evidence-backed (Section 22)

---

## Metrics Integrity

- [x] Evaluation results are real — computed from APS-04 `eval_relevance_labels`
- [x] Popularity baseline: P@5=0.6250, NDCG@10=0.5403, MRR=0.6807
- [x] Semantic baseline: P@5=0.1750, NDCG@10=0.1905, MRR=0.4392
- [x] NEXORA: P@5=0.2900, NDCG@10=0.2988, MRR=0.5687
- [x] Popularity outperformance honestly explained (label correlation with quality)
- [x] No metric is fabricated or rounded up
- [x] Limitations documented (position bias, 40/120 queries, no language stratification)

---

## Technical Accuracy

- [x] Architecture matches actual implementation (FastAPI + SQLite + FAISS)
- [x] Dataset facts match APS-04 actual values (28,630 rows, 1,200 users, 600 cold-start, etc.)
- [x] User journey matches actual API flow (`/search` → `/interactions` → profile rebuild)
- [x] No capability claimed that is not implemented or explicitly marked as planned
- [x] Cold-start behaviour documented correctly (explicit prefs, no behaviour reasons)
- [x] Multilingual retrieval verified (Hindi test case documented)
- [x] Hard filter design matches implementation (SQL predicates, not soft penalties)

---

## Quality Gate

- [x] No fake claims
- [x] No "best-in-class" assertions without supporting evidence
- [x] No college-assignment language
- [x] No unnecessary padding or filler sections
- [x] Consistent heading structure across all 22 documents
- [x] Tables render correctly in Markdown preview
- [x] Mermaid diagrams valid (test in mermaid.live)
- [x] No spelling errors in section headings
- [x] Document is understandable to a judge who has never seen the project

---

## PDF Final Check

- [ ] PDF generated from source files
- [ ] File name: `NEXORA_APS-04_Design_Submission.pdf`
- [ ] File size: under 25 MB
- [ ] All 22 sections present in PDF
- [ ] Diagrams visible (not raw Mermaid text)
- [ ] Tables formatted correctly
- [ ] Page breaks between major sections
- [ ] Cover page appears on page 1
- [ ] No `TODO` or placeholder text remaining
- [ ] PDF opens correctly in Adobe Acrobat and browser PDF viewer

---

## Submission Platform

- [ ] Logged in with team lead account
- [ ] Problem statement shown is APS-04 (verify before uploading)
- [ ] PDF uploaded as primary file
- [ ] File count ≤ 10
- [ ] Each file ≤ 25 MB
- [ ] Confirmation screenshot saved
- [ ] Submission locked (no second attempt available)

---

*Last updated: 2 September 2026*
*Submission deadline: 2 September 2026*
