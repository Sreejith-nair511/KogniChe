# 9. Hybrid Retrieval

## 9.1 Why Two Retrieval Methods

Semantic retrieval and structured retrieval solve different problems. Combining them without separating their roles produces a common failure mode: semantically irrelevant but query-adjacent items appearing in results, or hard-constraint violations being "compensated" by high similarity scores.

NEXORA uses them as sequential gates, not competing signals.

## 9.2 Structured Retrieval — Hard Constraints

**Purpose:** Define the feasible set. Nothing outside this set is ever shown.

**Implementation:** SQL predicates on APS-04. Constraints are applied per entity type.

### Hotels
```sql
WHERE h.status = 'active'
  AND (city_id = ? IF specified)
  AND (star_rating >= ? IF specified)
  -- Budget: via join on hotel_room_types
  AND EXISTS (
    SELECT 1 FROM hotel_room_types rt
    WHERE rt.hotel_id = h.hotel_id
      AND rt.status = 'active'
      AND CAST(rt.base_rate AS REAL) <= budget_max
  )
```

### POIs
```sql
WHERE p.status = 'active'
  AND (city_id = ? IF specified)
  AND (poi_category IN (?) IF specified)
  AND CAST(p.entry_cost AS REAL) <= budget_max
  AND (accessibility = ? IF specified)
```

### Tour Packages
```sql
WHERE tp.status = 'active'
  AND (city_id = ? IF specified)
  AND (theme IN (?) IF specified)
  AND tp.duration_days <= duration_max
  AND CAST(tp.base_price AS REAL) <= budget_max
  AND (',' || tp.languages_offered || ',') LIKE '%,lang,%'
```

**Critical design decision:** Money fields in APS-04 are stored as `TEXT` per Rule R3. `CAST(base_price AS REAL)` is used **only for comparison**, never for arithmetic or display. Display values are passed through as strings.

## 9.3 Semantic Retrieval — Intent Matching

**Purpose:** Find items whose meaning is closest to the user's intent, regardless of exact keyword overlap.

**Implementation:**
1. The enriched query is encoded: `embed("adventure package 4 days Coorg themes: adventure in Coorg India")`
2. A FAISS `IndexFlatIP` search retrieves the top-150 nearest vectors
3. Inner product on normalized vectors = cosine similarity

**Why multilingual-mpnet?**
The model is trained on 50+ languages. A Hindi query — `"परिवार के लिए होटल"` — produces a vector in the same semantic space as `"family hotel"`. No translation pipeline is needed.

**Item embedding text** is constructed at index time from:
- Item name
- Category / property type / theme
- Description (first 300 characters)
- City and country
- Tags (POIs) / inclusions (packages)

This ensures the embedding captures the item's semantic identity, not just its title.

## 9.4 Candidate Fusion

```
eligible_set    = {(type, id) from hard filter}        # e.g., 18 packages
semantic_hits   = [(type, id, similarity) from FAISS]  # e.g., 150 items

candidates = [
  hit for hit in semantic_hits
  if (hit.type, hit.id) in eligible_set
]

# If candidates < 5: augment with popularity-sorted eligible items
# These get semantic_score = 0.3 (below any real semantic hit)
```

**Result:** A candidate pool of ~10–50 items that are both semantically relevant AND constraint-compliant.

## 9.5 Pipeline Statistics (Real, from APS-04)

For a query against the full catalogue:

| Stage | Count |
|-------|-------|
| Total indexed items | 1,260 |
| After hard filter (typical) | 15–200 depending on constraints |
| Semantic candidates (top-150) | Up to 150 |
| After intersection | 5–50 |
| After MMR (final) | 10 |

The `retrieval_telemetry` object in every API response exposes these exact numbers for every real query.

## 9.6 Why Not Soft Constraints

A common alternative is to keep all items in the semantic search space and apply soft penalties for constraint violations. This has two problems:

1. **User trust.** A user who says "under ₹5,000" and sees a ₹12,000 result — even ranked 10th — will not trust the system.
2. **Evaluation integrity.** APS-04 eval queries carry `filters_json` with hard constraints. A result that violates them should not receive relevance credit.

Hard filtering is non-negotiable in NEXORA.
