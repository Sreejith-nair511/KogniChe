# APS-04 — your data model

**Hyper-Personalized Recommendation Engine**  
Kognivera Hackathon 2026 · Travel & Tourism · data model v1.1.0-rc1

> **The problem statement itself, the 24-hour MVP scope and the XR device requirement live in the hackathon application**, on your statement's page. This document is the data you have been given to build it with: every table, every field, and what each one is for.

---

You have **28,630 rows across 15 tables**. 13 of them are the tables this statement is built on; the remaining 2 are reference tables the others point at, included so the database works on its own.

All of it is in the `data/` folder beside this document: as `APS-04.db` (SQLite, indexed, ready to query), as CSV, and as DDL for Postgres and SQLite.

## What the data gives you

12,339 interactions across three deliberate cohorts — including 600 users with **zero** history so cold start is testable — plus 120 shared queries in three languages and 3,600 graded relevance labels.

## Watch out for this one

`position_in_list` is recorded so you can debias offline evaluation. Ignoring it is allowed; pretending it does not matter is not.

## The tables this statement is built on

| Table | Rows | What you use it for |
|---|---|---|
| `activities_poi` | 900 | Points of interest with real depth — cost, duration, carbon, hours and tags — because APS-09 optimises over exactly these fields. |
| `cities` | 60 | The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one. |
| `countries` | 30 | ISO country reference. Every city, currency default and calling code resolves here. |
| `currencies` | 25 | carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2). |
| `hotels` | 300 | Fewer, richer properties. Depth (reviews, room types, media) matters more than catalogue size —. |
| `languages` | 26 | Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model. |
| `tour_packages` | 60 | Curated catalogues are small in real life. The depth lives in package_components. |
| `user_preferences` | 1,200 | Explicit preference signal. PS-04's language-preference requirement reads from here. |
| `users` | 1,200 | The traveller identity every personalisation hangs off. Segmented heavy / light / cold_start so APS-04 can prove cold start. |
| `eval_queries` | 120 | 120 shared natural-language queries. Without them we get thirteen incomparable precision@k numbers. |
| `eval_relevance_labels` | 3,600 | Graded 0–3 relevance for ~30 candidates per query. This is the shared ground truth that turns a list into a leaderboard. |
| `hotel_reviews` | 7,500 | the single most important density ratio in the pack. ~25 per hotel, mixed languages and traveller types, because PS-02's flagship feature is summarising them into balanced pros and cons. |
| `user_interactions` | 12,339 | heavy users with long histories plus a deliberate cold-start cohort with none. One event per user makes everyone cold and APS-04 undemonstrable. |

## Reference tables, included so the database is valid

You will mostly join through these rather than think about them.

| Table | Rows | What it is |
|---|---|---|
| `hotel_room_types` | 1,200 | The bookable unit. APS-05's no-oversell guarantee is defended at this grain. |
| `categories` | 70 | One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart. |

## How they fit together

Open `02_DATA_MODEL_DIAGRAM.html` in a browser for the clickable version — it shows these tables and nothing else. Download it first; it will not render inside SharePoint.

Some tables point at "any bookable thing" using an `(entity_type, entity_id)` pair rather than a typed foreign key. That is deliberate: it is what lets one feature refer to a hotel, a flight, a point of interest or a package without a separate join table for each. The legal values of `entity_type` are in `data/enums.json`.

---

## Every field, table by table

Columns marked **PK** are the primary key. **FK** shows what a column points at. Enum columns list their legal values — anything else is rejected by the conformance check.

### `categories`

*Reference & geography · 70 rows · IDs start `cat_` · reference table*

One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `category_id` | text | **PK** | cat_ prefixed. |
| `code` | text | UNIQUE · NOT NULL | snake_case. |
| `label` | text | NOT NULL |  |
| `parent_category_id` | text | FK → `categories.category_id` | Null for top-level; self-referencing. |
| `applies_to` | text | NOT NULL | poi | package | expense | mixed. |
| `updated_at` | timestamptz | NOT NULL |  |

### `currencies`

*Reference & geography · 25 rows · IDs start `cur_`*

carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `currency_id` | text | **PK** | cur_ prefixed. |
| `iso4217` | char(3) | UNIQUE · NOT NULL | e.g. INR. |
| `name` | text | NOT NULL |  |
| `symbol` | text | NOT NULL |  |
| `minor_unit_exponent` | smallint | NOT NULL | 0 for JPY/KRW, 2 default, 3 for KWD/BHD. |
| `display_locale` | text | NOT NULL | BCP-47 locale used for formatting. |
| `updated_at` | timestamptz | NOT NULL |  |

### `languages`

*Reference & geography · 26 rows · IDs start `lng_`*

Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `language_id` | text | **PK** | lng_ prefixed. |
| `bcp47` | text | UNIQUE · NOT NULL | e.g. ta, hi, en-IN — never 'Tamil'. |
| `english_name` | text | NOT NULL |  |
| `native_name` | text | NOT NULL |  |
| `script` | text | NOT NULL | ISO-15924, e.g. Taml, Deva, Latn. |
| `rtl` | bool | NOT NULL | Right-to-left rendering flag. |
| `tts_supported` | bool | NOT NULL | Relevant to PS-13 voice output. |
| `updated_at` | timestamptz | NOT NULL |  |

### `countries`

*Reference & geography · 30 rows · IDs start `cnt_`*

ISO country reference. Every city, currency default and calling code resolves here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `country_id` | text | **PK** | Canonical ID, cnt_ prefixed. |
| `iso2` | char(2) | UNIQUE · NOT NULL | ISO-3166-1 alpha-2, e.g. IN. |
| `iso3` | char(3) | UNIQUE · NOT NULL | ISO-3166-1 alpha-3, e.g. IND. |
| `name` | text | NOT NULL | English short name. |
| `default_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL | ISO-4217 code. |
| `calling_code` | text | NOT NULL | E.164 country calling code, e.g. +91. |
| `region` | text | NOT NULL | UN sub-region grouping. |
| `updated_at` | timestamptz | NOT NULL | Rule R4: UTC, ISO-8601 with offset. |

### `cities`

*Reference & geography · 60 rows · IDs start `cty_`*

The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `city_id` | text | **PK** | cty_ prefixed. |
| `name` | text | NOT NULL | City name. |
| `state` | text |  | State / province, nullable for city-states. |
| `country_id` | text | FK → `countries.country_id` · NOT NULL |  |
| `country_code` | char(2) | NOT NULL | Denormalised ISO2 for convenient joins. |
| `lat` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `lng` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `timezone` | text | NOT NULL | IANA zone, e.g. Asia/Kolkata. |
| `region` | text | NOT NULL | Domestic region grouping, e.g. South India. |
| `population` | int |  | Approximate, for demand weighting. |
| `season_profile` | text | NOT NULL · one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` | Dominant season at the peak travel window. |
| `peak_months` | text | NOT NULL | Comma-separated month numbers, e.g. 10,11,12. |
| `primary_language` | text | FK → `languages.bcp47` · NOT NULL | Rule R6: BCP-47 tag. |
| `description` | text |  | One-paragraph orientation blurb, used by PS-13. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `hotels`

*Supply & catalogue · 300 rows · IDs start `htl_`*

Fewer, richer properties. Depth (reviews, room types, media) matters more than catalogue size —.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `hotel_id` | text | **PK** | htl_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `name` | text | NOT NULL | ~3% near-duplicate names injected deliberately. |
| `property_type` | text | NOT NULL · one of `hotel`, `resort`, `homestay`, `hostel`, `apartment`, `boutique`, `heritage`, `guesthouse` |  |
| `star_rating` | smallint | NOT NULL | 1–5, CHECK constrained. |
| `guest_score` | decimal(2,1) |  | 0.0–10.0; null for a handful of new properties. |
| `review_count` | int | NOT NULL | Denormalised count, must agree with hotel_reviews. |
| `address_line` | text | NOT NULL |  |
| `lat` | decimal(9,6) | NOT NULL |  |
| `lng` | decimal(9,6) | NOT NULL |  |
| `distance_to_centre_km` | decimal(6,2) | NOT NULL | PS-02 filter: distance to a landmark. |
| `description` | text | NOT NULL | Plausible prose, embeddable. |
| `base_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `checkin_time` | text | NOT NULL | Local HH:MM at the property. |
| `checkout_time` | text | NOT NULL |  |
| `chain_code` | text |  | Null for independents. |
| `has_xr_scene` | bool | NOT NULL | PS-05 / APS-07 — does an immersive preview exist. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `tour_packages`

*Supply & catalogue · 60 rows · IDs start `pkg_`*

Curated catalogues are small in real life. The depth lives in package_components.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `package_id` | text | **PK** | pkg_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL | Primary destination. |
| `name` | text | NOT NULL |  |
| `theme` | text | NOT NULL · one of `adventure`, `honeymoon`, `pilgrimage`, `family`, `heritage`, `wellness`, `wildlife`, `food_trail` |  |
| `tier` | text | NOT NULL · one of `standard`, `deluxe`, `premium` |  |
| `duration_days` | smallint | NOT NULL |  |
| `duration_nights` | smallint | NOT NULL |  |
| `base_price` | decimal(12,2) | NOT NULL | the figure PS-04 reprices live. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `min_group_size` | smallint | NOT NULL |  |
| `max_group_size` | smallint | NOT NULL |  |
| `difficulty` | text | NOT NULL | easy | moderate | challenging. |
| `languages_offered` | text | NOT NULL | Comma-separated BCP-47 — PS-04 filters on this. |
| `inclusions` | text | NOT NULL | Prose summary. |
| `exclusions` | text | NOT NULL |  |
| `description` | text | NOT NULL |  |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `users`

*Identity & preference · 1,200 rows · IDs start `usr_`*

The traveller identity every personalisation hangs off. Segmented heavy / light / cold_start so APS-04 can prove cold start.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `user_id` | text | **PK** | usr_ prefixed. |
| `display_name` | text | NOT NULL | Synthetic — no real people (content policy). |
| `email` | text | UNIQUE · NOT NULL | Synthetic @example.invalid addresses only. |
| `home_city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `home_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `locale` | text | FK → `languages.bcp47` · NOT NULL | UI language, BCP-47. |
| `budget_band` | text | NOT NULL · one of `shoestring`, `value`, `mid`, `premium`, `luxury` |  |
| `travel_style` | text | NOT NULL · one of `budget`, `comfort`, `luxury`, `adventure`, `slow`, `cultural`, `wellness` |  |
| `traveller_type` | text | NOT NULL · one of `solo`, `couple`, `family`, `business`, `friends`, `senior`, `backpacker` |  |
| `segment` | text | NOT NULL · one of `heavy`, `light`, `cold_start` | heavy / light / cold_start cohorts. |
| `date_of_signup` | date | NOT NULL |  |
| `loyalty_tier` | text |  | none | silver | gold — nullable by design. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `activities_poi`

*Supply & catalogue · 900 rows · IDs start `poi_`*

Points of interest with real depth — cost, duration, carbon, hours and tags — because APS-09 optimises over exactly these fields.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `poi_id` | text | **PK** | poi_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `name` | text | NOT NULL |  |
| `category_id` | text | FK → `categories.category_id` · NOT NULL |  |
| `poi_category` | text | NOT NULL · one of `heritage`, `nature`, `museum`, `religious`, `adventure`, `food`, `shopping`, `nightlife`, `beach`, `wildlife`, `wellness`, `viewpoint` | Denormalised top-level category. |
| `lat` | decimal(9,6) | NOT NULL |  |
| `lng` | decimal(9,6) | NOT NULL |  |
| `typical_duration_minutes` | int | NOT NULL | APS-09 constraint input. |
| `entry_cost` | decimal(12,2) | NOT NULL | 0.00 where free. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `carbon_kg` | decimal(8,3) | NOT NULL | On-site footprint estimate. |
| `popularity_score` | smallint | NOT NULL | 0–100, drives APS-04 baseline ranking. |
| `value_score` | smallint | NOT NULL | 0–100, the 'value' objective in APS-09. |
| `opens_at` | text |  | Local HH:MM; null where always open. |
| `closes_at` | text |  |  |
| `closed_days` | text |  | Comma-separated 0–6, 0 = Monday. |
| `best_season` | text | one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` |  |
| `accessibility` | text | NOT NULL | step_free | partial | none. |
| `tags` | text | NOT NULL | Comma-separated free tags for hybrid retrieval. |
| `description` | text | NOT NULL | Plausible prose. |
| `has_xr_scene` | bool | NOT NULL | PS-05 / APS-07. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `eval_queries`

*Signals & evaluation · 120 rows · IDs start `evq_`*

120 shared natural-language queries. Without them we get thirteen incomparable precision@k numbers.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `query_id` | text | **PK** | evq_ prefixed. |
| `query_text` | text | NOT NULL |  |
| `language` | text | FK → `languages.bcp47` · NOT NULL | Includes hi and ta queries for the multilingual requirement. |
| `intent` | text | NOT NULL · one of `budget_stay`, `family_stay`, `luxury_stay`, `heritage_poi`, `nature_poi`, `food_poi`, `adventure_package`, `honeymoon_package`, `accessibility`, `pet_friendly` |  |
| `target_entity_type` | text | NOT NULL · one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` |  |
| `city_id` | text | FK → `cities.city_id` | Null for city-agnostic queries. |
| `persona_user_id` | text | FK → `users.user_id` | The user whose profile the query should be personalised to. |
| `filters_json` | text | NOT NULL | JSON string of the hard filters a correct system must apply. |
| `k` | smallint | NOT NULL | The k at which precision@k is reported. |
| `notes` | text |  |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `eval_relevance_labels`

*Signals & evaluation · 3,600 rows · IDs start `evl_`*

Graded 0–3 relevance for ~30 candidates per query. This is the shared ground truth that turns a list into a leaderboard.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `label_id` | text | **PK** | evl_ prefixed. |
| `query_id` | text | FK → `eval_queries.query_id` · NOT NULL |  |
| `entity_type` | text | NOT NULL · one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` |  |
| `entity_id` | text | NOT NULL |  |
| `grade` | smallint | NOT NULL | 0 irrelevant, 1 marginal, 2 relevant, 3 ideal. |
| `rationale` | text |  | Why the grade was given — useful when a team disputes one. |
| `labeller` | text | NOT NULL | Synthetic labeller identifier. |
| `updated_at` | timestamptz | NOT NULL |  |

*Unique together:* `(query_id, entity_type, entity_id)`

### `hotel_room_types`

*Supply & catalogue · 1,200 rows · IDs start `rmt_` · reference table*

The bookable unit. APS-05's no-oversell guarantee is defended at this grain.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `room_type_id` | text | **PK** | rmt_ prefixed. |
| `hotel_id` | text | FK → `hotels.hotel_id` · NOT NULL |  |
| `name` | text | NOT NULL | e.g. Deluxe Garden View. |
| `max_occupancy` | smallint | NOT NULL |  |
| `max_adults` | smallint | NOT NULL |  |
| `max_children` | smallint | NOT NULL |  |
| `bed_config` | text | NOT NULL · one of `single`, `twin`, `double`, `queen`, `king`, `bunk`, `twin_double` |  |
| `size_sqm` | smallint |  |  |
| `base_rate` | decimal(12,2) | NOT NULL | NUMERIC, never FLOAT. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL | always paired with the amount. |
| `total_units` | int | NOT NULL | Deliberately scarce on some rows so APS-05 has contention. |
| `smoking_allowed` | bool | NOT NULL |  |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `user_interactions`

*Signals & evaluation · 12,339 rows · IDs start `uix_`*

heavy users with long histories plus a deliberate cold-start cohort with none. One event per user makes everyone cold and APS-04 undemonstrable.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `interaction_id` | text | **PK** | uix_ prefixed. |
| `user_id` | text | FK → `users.user_id` · NOT NULL |  |
| `entity_type` | text | NOT NULL · one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` |  |
| `entity_id` | text | NOT NULL |  |
| `interaction_type` | text | NOT NULL · one of `view`, `click`, `like`, `save`, `book`, `dismiss`, `share`, `search` |  |
| `occurred_at` | timestamptz | NOT NULL |  |
| `dwell_seconds` | int |  | Null for non-view events. |
| `position_in_list` | smallint |  | Rank at which the item was shown — needed for unbiased offline eval. |
| `query_text` | text |  | Set for interaction_type = search. |
| `query_language` | text | FK → `languages.bcp47` |  |
| `channel` | text | NOT NULL · one of `web`, `mobile_app`, `partner`, `call_centre`, `agent` |  |
| `session_id` | text | NOT NULL |  |
| `implicit_rating` | decimal(3,2) |  | Derived signal, provided for convenience. |

### `user_preferences`

*Identity & preference · 1,200 rows · IDs start `prf_`*

Explicit preference signal. PS-04's language-preference requirement reads from here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `preference_id` | text | **PK** | prf_ prefixed. |
| `user_id` | text | FK → `users.user_id` · UNIQUE · NOT NULL | One row per user. |
| `preferred_languages` | text | NOT NULL | Comma-separated BCP-47 tags, most-preferred first. |
| `guide_language` | text | FK → `languages.bcp47` | PS-04 — preferred language for guide/tour delivery. |
| `interests` | text | NOT NULL | Comma-separated category codes. |
| `dietary_flags` | text |  | vegetarian | vegan | halal | jain | none. |
| `accessibility_needs` | text |  | step_free | hearing | vision | none. |
| `preferred_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `max_daily_budget` | decimal(12,2) |  | decimal, paired with currency below. |
| `max_daily_budget_currency` | char(3) | FK → `currencies.iso4217` |  |
| `pace` | text | NOT NULL | relaxed | balanced | packed — feeds PS-01 and APS-09. |
| `updated_at` | timestamptz | NOT NULL |  |

### `hotel_reviews`

*Supply & catalogue · 7,500 rows · IDs start `rvw_`*

the single most important density ratio in the pack. ~25 per hotel, mixed languages and traveller types, because PS-02's flagship feature is summarising them into balanced pros and cons.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `review_id` | text | **PK** | rvw_ prefixed. |
| `hotel_id` | text | FK → `hotels.hotel_id` · NOT NULL |  |
| `user_id` | text | FK → `users.user_id` | Nullable — some reviews are from non-registered guests. |
| `rating` | smallint | NOT NULL | 1–10. |
| `title` | text |  |  |
| `body` | text | NOT NULL | Plausible prose, 40–120 words. |
| `language` | text | FK → `languages.bcp47` · NOT NULL | Rule R6: mixed en-IN / hi / ta / ml / bn. |
| `traveller_type` | text | NOT NULL · one of `solo`, `couple`, `family`, `business`, `friends`, `senior`, `backpacker` |  |
| `stay_date` | date | NOT NULL | Rule R4: zoneless. |
| `room_type_id` | text | FK → `hotel_room_types.room_type_id` |  |
| `helpful_votes` | int | NOT NULL |  |
| `has_photo` | bool | NOT NULL |  |
| `sentiment_hint` | decimal(3,2) |  | -1.00..1.00, provided for calibration only. |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

---

## The rules that apply to these fields

| # | Rule |
|---|---|
| R1 | **Additive only.** Add columns, tables and stores freely. Never rename, drop or repurpose a field that came with the data. |
| R2 | **IDs are opaque prefixed strings** — `htl_a91f3c`. Never integers, never parsed for meaning. |
| R3 | **Money is a pair**: a 2-place decimal plus an ISO-4217 currency code. Never a float. |
| R4 | **Time is ISO-8601 with an offset.** `_at` fields carry an offset; `_date` fields have no zone. |
| R5 | **Enums are lowercase snake_case** and the legal values are in `data/enums.json`. |
| R6 | **Language is a BCP-47 tag** — `ta`, not "Tamil". |
| R7 | **Geography is WGS-84** to 6 decimal places, `lat` and `lng` together or not at all. |
| R8 | **Nothing is hard-deleted.** Rows carry `status` and `updated_at`. |

Add whatever you like beside these fields — new columns, new tables, your own vector store, your own services. That is the point of R1. What you must not do is rename or re-key the fields that came with the data, because that is what would stop sixteen independent builds being put together afterwards.

`data/WORKING_WITH_THE_DATA.md` has the loading instructions, including how to read money without corrupting it. `tools/validate_conformance.py` tells you in thirty seconds whether you are still conformant.
