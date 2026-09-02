# 2. Problem Understanding

## What Traditional Travel Search Gets Wrong

Travel search as commonly implemented is a keyword matching and popularity ranking system. When a user submits a query, the system retrieves items that contain the query terms and sorts them by some global relevance or recency signal.

This approach has four compounding failures:

### 2.1 The Identity Problem

The same query — "family beach holiday" — should surface different results for:
- A budget family of four from Chennai (INR budget, Tamil language, accessibility needs)
- A premium couple from Mumbai (luxury resort preference, INR, no dietary flags)
- A backpacker (hostel, minimal cost, solo)

Traditional retrieval cannot distinguish these users. NEXORA builds a profile from the APS-04 `users`, `user_preferences`, and `user_interactions` tables and uses it to personalise every stage of retrieval.

### 2.2 The Cold-Start Problem

Of the 1,200 users in APS-04, **600 have zero interaction history** (segment: `cold_start`). A system that relies purely on behavioural signals cannot serve them.

NEXORA addresses cold-start through: explicit preferences from `user_preferences`, query semantics, catalogue quality signals (popularity, rating), and controlled diversity. The profile maturity system (`cold_start → early → learning → mature`) dynamically adjusts ranking weight towards semantic and preference signals when history is sparse.

### 2.3 The Constraint Violation Problem

Hard constraints — budget, location, star rating, language — are non-negotiable requirements that many similarity-based systems violate. A user with a budget of ₹5,000/night should never see a ₹15,000 result, regardless of its semantic similarity score.

NEXORA enforces hard filters as SQL predicates before any ML scoring. The filter and ranking stages are explicitly separated.

### 2.4 The Multilingual Problem

The APS-04 evaluation set contains queries in English (`en-IN`), Hindi (`hi`), Tamil (`ta`), and Malayalam (`ml`). Hotel reviews span eight languages. A retrieval system that works only on English queries cannot serve the majority of Indian travellers.

NEXORA uses `paraphrase-multilingual-mpnet-base-v2`, a 768-dimensional model trained on 50+ languages, enabling cross-lingual semantic retrieval without translation.

### 2.5 The Explainability Gap

Users do not trust opaque recommendation lists. "You might like this" is not a reason. NEXORA generates grounded explanations — per recommendation — showing which profile signals, behavioural evidence, and query constraints contributed to each result.

### 2.6 The Static Ranking Problem

A user's intent shifts within a session. Someone who came in searching for "budget guesthouses" and then liked two heritage properties is signalling a change in intent. Session learning captures this and updates ranking in real time.

## How NEXORA Frames the Problem

Traditional search answers:
> "What items in the catalogue match this query?"

NEXORA answers:
> "What is the best set of items for **this specific traveller**, given their stated preferences, their interaction history, their current session intent, the hard constraints in their query, and the evidence in the catalogue — and can we explain it?"
