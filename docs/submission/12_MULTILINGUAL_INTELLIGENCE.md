# 12. Multilingual Intelligence

## 12.1 The Multilingual Requirement

The APS-04 evaluation set includes queries in four languages:

| Language | BCP-47 | Eval Queries | Hotel Reviews |
|----------|--------|-------------|---------------|
| English (Indian) | en-IN | 80 | 3,109 |
| Hindi | hi | 16 | 1,252 |
| Tamil | ta | 16 | 752 |
| Malayalam | ml | 8 | 539 |
| Bengali | bn | — | 491 |
| Marathi | mr | — | 442 |
| Telugu | te | — | 437 |
| English (British) | en-GB | — | 478 |

A recommendation system that works only on English queries cannot be evaluated against the full APS-04 eval set and cannot serve the majority of Indian travellers.

## 12.2 Approach: Native Multilingual Embedding

**Model:** `paraphrase-multilingual-mpnet-base-v2`
**Dimension:** 768
**Languages:** 50+
**Architecture:** Fine-tuned XLM-RoBERTa with multilingual parallel corpus training

The model maps semantically equivalent text in different languages to nearby points in the same 768-dimensional space. This means:

- `"family hotel"` (en-IN)
- `"परिवार के लिए होटल"` (hi)
- `"குடும்பத்திற்கான ஹோட்டல்"` (ta)

...all produce similar vectors. A FAISS search on any of these queries returns the same semantically relevant hotel items — without translation.

## 12.3 Implementation

### Language Detection
```python
from langdetect import detect

lang = detect(query_text)  # Returns ISO 639-1 code
bcp47_mapping = {
    "hi": "hi",
    "ta": "ta",
    "ml": "ml",
    "bn": "bn",
    "mr": "mr",
    "te": "te",
    "kn": "kn",
    "en": "en-IN",
}
detected_language = bcp47_mapping.get(lang, "en-IN")
```

### Constraint Extraction on Non-English Queries
City name lookup and budget patterns are extracted from the Latin-script transliterations where present. For fully non-Latin queries (pure Devanagari, Tamil), constraints fall back to API-level `filters` object. The semantic signal still works correctly.

### Query Embedding
```python
# Works identically for all languages
query_embedding = model.encode(
    ["परिवार के लिए होटल"],
    normalize_embeddings=True
)
# → 768-d vector in shared multilingual space
```

### Cross-Language Retrieval

Item texts are embedded in English (the language of APS-04 data). Query texts can be in any supported language. The multilingual model bridges the gap. This is **cross-lingual retrieval** — verified in end-to-end testing.

## 12.4 Verified Test Result

From the end-to-end test:

```
Query: "परिवार के लिए होटल"  (Hindi: "hotel for family")
detected_language: hi
results: 3
top_result: Heritage Residency Inn (hotel)
entity_type: hotel
```

The system correctly identified the language, retrieved relevant hotels, and returned real APS-04 results. No translation service was used.

## 12.5 Limitations

- **Constraint extraction** from non-Latin scripts is partial. City names in pure Devanagari are not yet mapped to `city_id`. Explicit `city_id` filter in the API request is the reliable path for non-English structured constraints.
- **Explanation text** is generated in English regardless of query language. Localized explanation text is a planned future enhancement.
- **Review intelligence** from multilingual reviews uses `sentiment_hint` (a numeric field) rather than text analysis, so language of review is not a barrier.

## 12.6 What Is Not Claimed

- The system does **not** claim to generate responses in the user's query language
- The system does **not** claim equal recall quality across all languages (Hindi/Tamil have fewer training examples in some domains)
- Multilingual evaluation metrics (NDCG per language) are not yet separated — this is a limitation documented in Section 15 (Evaluation)
