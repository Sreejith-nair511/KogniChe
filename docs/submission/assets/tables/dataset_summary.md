# APS-04 Dataset Summary Table

| Table | Rows | Primary Key Prefix | Used By |
|-------|------|--------------------|---------|
| users | 1,200 | usr_ | Profile, evaluation, cold-start |
| user_preferences | 1,200 | prf_ | Profile (explicit signals) |
| user_interactions | 12,339 | uix_ | Profile (behaviour), evaluation |
| hotels | 300 | htl_ | Catalogue, hard filter, embedding |
| hotel_room_types | 1,200 | rmt_ | Budget hard filter |
| hotel_reviews | 7,500 | rvw_ | Rating signal, sentiment |
| activities_poi | 900 | poi_ | Catalogue, hard filter, embedding |
| tour_packages | 60 | pkg_ | Catalogue, hard filter, embedding |
| cities | 60 | cty_ | City constraint resolution |
| countries | 30 | cnt_ | Geographic joins |
| currencies | 25 | cur_ | Display, validation |
| languages | 26 | lng_ | BCP-47 validation |
| categories | 70 | cat_ | Category label joins |
| eval_queries | 120 | evq_ | Evaluation ground truth |
| eval_relevance_labels | 3,600 | evl_ | Evaluation grades (0–3) |

## User Cohorts

| Segment | Users | Interactions | Avg Per User |
|---------|-------|-------------|-------------|
| cold_start | 600 | 0 | 0.0 |
| light | 400 | 3,881 | 9.7 |
| heavy | 200 | 8,458 | 42.3 |
| **Total** | **1,200** | **12,339** | **10.3** |

## Evaluation Set

| Language | Queries | % of Total |
|----------|---------|-----------|
| en-IN | 80 | 66.7% |
| hi | 16 | 13.3% |
| ta | 16 | 13.3% |
| ml | 8 | 6.7% |
| **Total** | **120** | **100%** |

## Relevance Label Distribution

| Grade | Meaning | Count | % |
|-------|---------|-------|---|
| 3 | Ideal | 257 | 7.1% |
| 2 | Relevant | 490 | 13.6% |
| 1 | Marginal | 892 | 24.8% |
| 0 | Irrelevant | 1,961 | 54.5% |
| **Total** | | **3,600** | |

## Interaction Signal Distribution

| Type | Count | % |
|------|-------|---|
| view | 4,918 | 39.9% |
| click | 2,264 | 18.4% |
| search | 1,292 | 10.5% |
| like | 1,033 | 8.4% |
| save | 845 | 6.9% |
| dismiss | 725 | 5.9% |
| book | 453 | 3.7% |
| share | 362 | 2.9% |
| others | 447 | 3.6% |
