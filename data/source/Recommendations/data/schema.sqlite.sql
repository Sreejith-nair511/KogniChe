-- KV Hackathon 2026 · travel data model v1.1.0-rc1
-- Only the 15 tables this problem statement needs.

-- SQLite has no DECIMAL type, and NUMERIC affinity would turn '8500.00' into the
-- float 8500.0. Money columns are therefore TEXT so the exact value survives.
PRAGMA foreign_keys = ON;

-- categories  (Reference & geography)
CREATE TABLE categories (
  category_id                  TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  parent_category_id           TEXT,
  applies_to                   TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)
);

-- currencies  (Reference & geography)
CREATE TABLE currencies (
  currency_id                  TEXT PRIMARY KEY,
  iso4217                      TEXT NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  symbol                       TEXT NOT NULL,
  minor_unit_exponent          INTEGER NOT NULL,
  display_locale               TEXT NOT NULL,
  updated_at                   TEXT NOT NULL
);

-- languages  (Reference & geography)
CREATE TABLE languages (
  language_id                  TEXT PRIMARY KEY,
  bcp47                        TEXT NOT NULL UNIQUE,
  english_name                 TEXT NOT NULL,
  native_name                  TEXT NOT NULL,
  script                       TEXT NOT NULL,
  rtl                          INTEGER NOT NULL,
  tts_supported                INTEGER NOT NULL,
  updated_at                   TEXT NOT NULL
);

-- countries  (Reference & geography)
CREATE TABLE countries (
  country_id                   TEXT PRIMARY KEY,
  iso2                         TEXT NOT NULL UNIQUE,
  iso3                         TEXT NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  default_currency             TEXT NOT NULL,
  calling_code                 TEXT NOT NULL,
  region                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (default_currency) REFERENCES currencies(iso4217)
);

-- cities  (Reference & geography)
CREATE TABLE cities (
  city_id                      TEXT PRIMARY KEY,
  name                         TEXT NOT NULL,
  state                        TEXT,
  country_id                   TEXT NOT NULL,
  country_code                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  timezone                     TEXT NOT NULL,
  region                       TEXT NOT NULL,
  population                   INTEGER,
  season_profile               TEXT NOT NULL,
  peak_months                  TEXT NOT NULL,
  primary_language             TEXT NOT NULL,
  description                  TEXT,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (country_id) REFERENCES countries(country_id),
  FOREIGN KEY (primary_language) REFERENCES languages(bcp47)
);

-- hotels  (Supply & catalogue)
CREATE TABLE hotels (
  hotel_id                     TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  property_type                TEXT NOT NULL,
  star_rating                  INTEGER NOT NULL,
  guest_score                  NUMERIC(2,1),
  review_count                 INTEGER NOT NULL,
  address_line                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  distance_to_centre_km        NUMERIC(6,2) NOT NULL,
  description                  TEXT NOT NULL,
  base_currency                TEXT NOT NULL,
  checkin_time                 TEXT NOT NULL,
  checkout_time                TEXT NOT NULL,
  chain_code                   TEXT,
  has_xr_scene                 INTEGER NOT NULL,
  status                       TEXT NOT NULL,
  created_at                   TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (base_currency) REFERENCES currencies(iso4217)
);

-- tour_packages  (Supply & catalogue)
CREATE TABLE tour_packages (
  package_id                   TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  theme                        TEXT NOT NULL,
  tier                         TEXT NOT NULL,
  duration_days                INTEGER NOT NULL,
  duration_nights              INTEGER NOT NULL,
  base_price                   TEXT NOT NULL,
  currency                     TEXT NOT NULL,
  min_group_size               INTEGER NOT NULL,
  max_group_size               INTEGER NOT NULL,
  difficulty                   TEXT NOT NULL,
  languages_offered            TEXT NOT NULL,
  inclusions                   TEXT NOT NULL,
  exclusions                   TEXT NOT NULL,
  description                  TEXT NOT NULL,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (currency) REFERENCES currencies(iso4217)
);

-- users  (Identity & preference)
CREATE TABLE users (
  user_id                      TEXT PRIMARY KEY,
  display_name                 TEXT NOT NULL,
  email                        TEXT NOT NULL UNIQUE,
  home_city_id                 TEXT NOT NULL,
  home_currency                TEXT NOT NULL,
  locale                       TEXT NOT NULL,
  budget_band                  TEXT NOT NULL,
  travel_style                 TEXT NOT NULL,
  traveller_type               TEXT NOT NULL,
  segment                      TEXT NOT NULL,
  date_of_signup               TEXT NOT NULL,
  loyalty_tier                 TEXT,
  status                       TEXT NOT NULL,
  created_at                   TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (home_city_id) REFERENCES cities(city_id),
  FOREIGN KEY (home_currency) REFERENCES currencies(iso4217),
  FOREIGN KEY (locale) REFERENCES languages(bcp47)
);

-- activities_poi  (Supply & catalogue)
CREATE TABLE activities_poi (
  poi_id                       TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  category_id                  TEXT NOT NULL,
  poi_category                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  typical_duration_minutes     INTEGER NOT NULL,
  entry_cost                   TEXT NOT NULL,
  currency                     TEXT NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  popularity_score             INTEGER NOT NULL,
  value_score                  INTEGER NOT NULL,
  opens_at                     TEXT,
  closes_at                    TEXT,
  closed_days                  TEXT,
  best_season                  TEXT,
  accessibility                TEXT NOT NULL,
  tags                         TEXT NOT NULL,
  description                  TEXT NOT NULL,
  has_xr_scene                 INTEGER NOT NULL,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (category_id) REFERENCES categories(category_id),
  FOREIGN KEY (currency) REFERENCES currencies(iso4217)
);

-- eval_queries  (Signals & evaluation)
CREATE TABLE eval_queries (
  query_id                     TEXT PRIMARY KEY,
  query_text                   TEXT NOT NULL,
  language                     TEXT NOT NULL,
  intent                       TEXT NOT NULL,
  target_entity_type           TEXT NOT NULL,
  city_id                      TEXT,
  persona_user_id              TEXT,
  filters_json                 TEXT NOT NULL,
  k                            INTEGER NOT NULL,
  notes                        TEXT,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (language) REFERENCES languages(bcp47),
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (persona_user_id) REFERENCES users(user_id)
);

-- eval_relevance_labels  (Signals & evaluation)
CREATE TABLE eval_relevance_labels (
  label_id                     TEXT PRIMARY KEY,
  query_id                     TEXT NOT NULL,
  entity_type                  TEXT NOT NULL,
  entity_id                    TEXT NOT NULL,
  grade                        INTEGER NOT NULL,
  rationale                    TEXT,
  labeller                     TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (query_id) REFERENCES eval_queries(query_id),
  UNIQUE (query_id, entity_type, entity_id)
);

-- hotel_room_types  (Supply & catalogue)
CREATE TABLE hotel_room_types (
  room_type_id                 TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  name                         TEXT NOT NULL,
  max_occupancy                INTEGER NOT NULL,
  max_adults                   INTEGER NOT NULL,
  max_children                 INTEGER NOT NULL,
  bed_config                   TEXT NOT NULL,
  size_sqm                     INTEGER,
  base_rate                    TEXT NOT NULL,
  currency                     TEXT NOT NULL,
  total_units                  INTEGER NOT NULL,
  smoking_allowed              INTEGER NOT NULL,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  FOREIGN KEY (currency) REFERENCES currencies(iso4217)
);

-- user_interactions  (Signals & evaluation)
CREATE TABLE user_interactions (
  interaction_id               TEXT PRIMARY KEY,
  user_id                      TEXT NOT NULL,
  entity_type                  TEXT NOT NULL,
  entity_id                    TEXT NOT NULL,
  interaction_type             TEXT NOT NULL,
  occurred_at                  TEXT NOT NULL,
  dwell_seconds                INTEGER,
  position_in_list             INTEGER,
  query_text                   TEXT,
  query_language               TEXT,
  channel                      TEXT NOT NULL,
  session_id                   TEXT NOT NULL,
  implicit_rating              NUMERIC(3,2),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (query_language) REFERENCES languages(bcp47)
);

-- user_preferences  (Identity & preference)
CREATE TABLE user_preferences (
  preference_id                TEXT PRIMARY KEY,
  user_id                      TEXT NOT NULL UNIQUE,
  preferred_languages          TEXT NOT NULL,
  guide_language               TEXT,
  interests                    TEXT NOT NULL,
  dietary_flags                TEXT,
  accessibility_needs          TEXT,
  preferred_currency           TEXT NOT NULL,
  max_daily_budget             TEXT,
  max_daily_budget_currency    TEXT,
  pace                         TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (guide_language) REFERENCES languages(bcp47),
  FOREIGN KEY (preferred_currency) REFERENCES currencies(iso4217),
  FOREIGN KEY (max_daily_budget_currency) REFERENCES currencies(iso4217)
);

-- hotel_reviews  (Supply & catalogue)
CREATE TABLE hotel_reviews (
  review_id                    TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  user_id                      TEXT,
  rating                       INTEGER NOT NULL,
  title                        TEXT,
  body                         TEXT NOT NULL,
  language                     TEXT NOT NULL,
  traveller_type               TEXT NOT NULL,
  stay_date                    TEXT NOT NULL,
  room_type_id                 TEXT,
  helpful_votes                INTEGER NOT NULL,
  has_photo                    INTEGER NOT NULL,
  sentiment_hint               NUMERIC(3,2),
  created_at                   TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (language) REFERENCES languages(bcp47),
  FOREIGN KEY (room_type_id) REFERENCES hotel_room_types(room_type_id)
);
