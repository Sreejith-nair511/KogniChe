-- KV Hackathon 2026 · travel data model v1.1.0-rc1
-- Only the 15 tables this problem statement needs.

CREATE EXTENSION IF NOT EXISTS vector;   -- optional, for embedding search

-- categories  (Reference & geography)
CREATE TABLE categories (
  category_id                  TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  parent_category_id           TEXT,
  applies_to                   TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- currencies  (Reference & geography)
CREATE TABLE currencies (
  currency_id                  TEXT PRIMARY KEY,
  iso4217                      CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  symbol                       TEXT NOT NULL,
  minor_unit_exponent          SMALLINT NOT NULL,
  display_locale               TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- languages  (Reference & geography)
CREATE TABLE languages (
  language_id                  TEXT PRIMARY KEY,
  bcp47                        TEXT NOT NULL UNIQUE,
  english_name                 TEXT NOT NULL,
  native_name                  TEXT NOT NULL,
  script                       TEXT NOT NULL,
  rtl                          BOOLEAN NOT NULL,
  tts_supported                BOOLEAN NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- countries  (Reference & geography)
CREATE TABLE countries (
  country_id                   TEXT PRIMARY KEY,
  iso2                         CHAR(2) NOT NULL UNIQUE,
  iso3                         CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  default_currency             CHAR(3) NOT NULL,
  calling_code                 TEXT NOT NULL,
  region                       TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- cities  (Reference & geography)
CREATE TABLE cities (
  city_id                      TEXT PRIMARY KEY,
  name                         TEXT NOT NULL,
  state                        TEXT,
  country_id                   TEXT NOT NULL,
  country_code                 CHAR(2) NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  timezone                     TEXT NOT NULL,
  region                       TEXT NOT NULL,
  population                   INTEGER,
  season_profile               TEXT NOT NULL CHECK (season_profile IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  peak_months                  TEXT NOT NULL,
  primary_language             TEXT NOT NULL,
  description                  TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- hotels  (Supply & catalogue)
CREATE TABLE hotels (
  hotel_id                     TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  property_type                TEXT NOT NULL CHECK (property_type IN ('hotel', 'resort', 'homestay', 'hostel', 'apartment', 'boutique', 'heritage', 'guesthouse')),
  star_rating                  SMALLINT NOT NULL,
  guest_score                  NUMERIC(2,1),
  review_count                 INTEGER NOT NULL,
  address_line                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  distance_to_centre_km        NUMERIC(6,2) NOT NULL,
  description                  TEXT NOT NULL,
  base_currency                CHAR(3) NOT NULL,
  checkin_time                 TEXT NOT NULL,
  checkout_time                TEXT NOT NULL,
  chain_code                   TEXT,
  has_xr_scene                 BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- tour_packages  (Supply & catalogue)
CREATE TABLE tour_packages (
  package_id                   TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  theme                        TEXT NOT NULL CHECK (theme IN ('adventure', 'honeymoon', 'pilgrimage', 'family', 'heritage', 'wellness', 'wildlife', 'food_trail')),
  tier                         TEXT NOT NULL CHECK (tier IN ('standard', 'deluxe', 'premium')),
  duration_days                SMALLINT NOT NULL,
  duration_nights              SMALLINT NOT NULL,
  base_price                   NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  min_group_size               SMALLINT NOT NULL,
  max_group_size               SMALLINT NOT NULL,
  difficulty                   TEXT NOT NULL,
  languages_offered            TEXT NOT NULL,
  inclusions                   TEXT NOT NULL,
  exclusions                   TEXT NOT NULL,
  description                  TEXT NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- users  (Identity & preference)
CREATE TABLE users (
  user_id                      TEXT PRIMARY KEY,
  display_name                 TEXT NOT NULL,
  email                        TEXT NOT NULL UNIQUE,
  home_city_id                 TEXT NOT NULL,
  home_currency                CHAR(3) NOT NULL,
  locale                       TEXT NOT NULL,
  budget_band                  TEXT NOT NULL CHECK (budget_band IN ('shoestring', 'value', 'mid', 'premium', 'luxury')),
  travel_style                 TEXT NOT NULL CHECK (travel_style IN ('budget', 'comfort', 'luxury', 'adventure', 'slow', 'cultural', 'wellness')),
  traveller_type               TEXT NOT NULL CHECK (traveller_type IN ('solo', 'couple', 'family', 'business', 'friends', 'senior', 'backpacker')),
  segment                      TEXT NOT NULL CHECK (segment IN ('heavy', 'light', 'cold_start')),
  date_of_signup               DATE NOT NULL,
  loyalty_tier                 TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- activities_poi  (Supply & catalogue)
CREATE TABLE activities_poi (
  poi_id                       TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  category_id                  TEXT NOT NULL,
  poi_category                 TEXT NOT NULL CHECK (poi_category IN ('heritage', 'nature', 'museum', 'religious', 'adventure', 'food', 'shopping', 'nightlife', 'beach', 'wildlife', 'wellness', 'viewpoint')),
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  typical_duration_minutes     INTEGER NOT NULL,
  entry_cost                   NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  popularity_score             SMALLINT NOT NULL,
  value_score                  SMALLINT NOT NULL,
  opens_at                     TEXT,
  closes_at                    TEXT,
  closed_days                  TEXT,
  best_season                  TEXT CHECK (best_season IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  accessibility                TEXT NOT NULL,
  tags                         TEXT NOT NULL,
  description                  TEXT NOT NULL,
  has_xr_scene                 BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- eval_queries  (Signals & evaluation)
CREATE TABLE eval_queries (
  query_id                     TEXT PRIMARY KEY,
  query_text                   TEXT NOT NULL,
  language                     TEXT NOT NULL,
  intent                       TEXT NOT NULL CHECK (intent IN ('budget_stay', 'family_stay', 'luxury_stay', 'heritage_poi', 'nature_poi', 'food_poi', 'adventure_package', 'honeymoon_package', 'accessibility', 'pet_friendly')),
  target_entity_type           TEXT NOT NULL CHECK (target_entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  city_id                      TEXT,
  persona_user_id              TEXT,
  filters_json                 TEXT NOT NULL,
  k                            SMALLINT NOT NULL,
  notes                        TEXT,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- eval_relevance_labels  (Signals & evaluation)
CREATE TABLE eval_relevance_labels (
  label_id                     TEXT PRIMARY KEY,
  query_id                     TEXT NOT NULL,
  entity_type                  TEXT NOT NULL CHECK (entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  entity_id                    TEXT NOT NULL,
  grade                        SMALLINT NOT NULL,
  rationale                    TEXT,
  labeller                     TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL,
  UNIQUE (query_id, entity_type, entity_id)
);

-- hotel_room_types  (Supply & catalogue)
CREATE TABLE hotel_room_types (
  room_type_id                 TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  name                         TEXT NOT NULL,
  max_occupancy                SMALLINT NOT NULL,
  max_adults                   SMALLINT NOT NULL,
  max_children                 SMALLINT NOT NULL,
  bed_config                   TEXT NOT NULL CHECK (bed_config IN ('single', 'twin', 'double', 'queen', 'king', 'bunk', 'twin_double')),
  size_sqm                     SMALLINT,
  base_rate                    NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  total_units                  INTEGER NOT NULL,
  smoking_allowed              BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- user_interactions  (Signals & evaluation)
CREATE TABLE user_interactions (
  interaction_id               TEXT PRIMARY KEY,
  user_id                      TEXT NOT NULL,
  entity_type                  TEXT NOT NULL CHECK (entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  entity_id                    TEXT NOT NULL,
  interaction_type             TEXT NOT NULL CHECK (interaction_type IN ('view', 'click', 'like', 'save', 'book', 'dismiss', 'share', 'search')),
  occurred_at                  TIMESTAMPTZ NOT NULL,
  dwell_seconds                INTEGER,
  position_in_list             SMALLINT,
  query_text                   TEXT,
  query_language               TEXT,
  channel                      TEXT NOT NULL CHECK (channel IN ('web', 'mobile_app', 'partner', 'call_centre', 'agent')),
  session_id                   TEXT NOT NULL,
  implicit_rating              NUMERIC(3,2)
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
  preferred_currency           CHAR(3) NOT NULL,
  max_daily_budget             NUMERIC(12,2),
  max_daily_budget_currency    CHAR(3),
  pace                         TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- hotel_reviews  (Supply & catalogue)
CREATE TABLE hotel_reviews (
  review_id                    TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  user_id                      TEXT,
  rating                       SMALLINT NOT NULL,
  title                        TEXT,
  body                         TEXT NOT NULL,
  language                     TEXT NOT NULL,
  traveller_type               TEXT NOT NULL CHECK (traveller_type IN ('solo', 'couple', 'family', 'business', 'friends', 'senior', 'backpacker')),
  stay_date                    DATE NOT NULL,
  room_type_id                 TEXT,
  helpful_votes                INTEGER NOT NULL,
  has_photo                    BOOLEAN NOT NULL,
  sentiment_hint               NUMERIC(3,2),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- foreign keys
ALTER TABLE categories ADD CONSTRAINT fk_categories_parent_category_id FOREIGN KEY (parent_category_id) REFERENCES categories(category_id);
ALTER TABLE countries ADD CONSTRAINT fk_countries_default_currency FOREIGN KEY (default_currency) REFERENCES currencies(iso4217);
ALTER TABLE cities ADD CONSTRAINT fk_cities_country_id FOREIGN KEY (country_id) REFERENCES countries(country_id);
ALTER TABLE cities ADD CONSTRAINT fk_cities_primary_language FOREIGN KEY (primary_language) REFERENCES languages(bcp47);
ALTER TABLE hotels ADD CONSTRAINT fk_hotels_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE hotels ADD CONSTRAINT fk_hotels_base_currency FOREIGN KEY (base_currency) REFERENCES currencies(iso4217);
ALTER TABLE tour_packages ADD CONSTRAINT fk_tour_packages_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE tour_packages ADD CONSTRAINT fk_tour_packages_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE users ADD CONSTRAINT fk_users_home_city_id FOREIGN KEY (home_city_id) REFERENCES cities(city_id);
ALTER TABLE users ADD CONSTRAINT fk_users_home_currency FOREIGN KEY (home_currency) REFERENCES currencies(iso4217);
ALTER TABLE users ADD CONSTRAINT fk_users_locale FOREIGN KEY (locale) REFERENCES languages(bcp47);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_category_id FOREIGN KEY (category_id) REFERENCES categories(category_id);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE eval_queries ADD CONSTRAINT fk_eval_queries_language FOREIGN KEY (language) REFERENCES languages(bcp47);
ALTER TABLE eval_queries ADD CONSTRAINT fk_eval_queries_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE eval_queries ADD CONSTRAINT fk_eval_queries_persona_user_id FOREIGN KEY (persona_user_id) REFERENCES users(user_id);
ALTER TABLE eval_relevance_labels ADD CONSTRAINT fk_eval_relevance_labels_query_id FOREIGN KEY (query_id) REFERENCES eval_queries(query_id);
ALTER TABLE hotel_room_types ADD CONSTRAINT fk_hotel_room_types_hotel_id FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id);
ALTER TABLE hotel_room_types ADD CONSTRAINT fk_hotel_room_types_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE user_interactions ADD CONSTRAINT fk_user_interactions_user_id FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE user_interactions ADD CONSTRAINT fk_user_interactions_query_language FOREIGN KEY (query_language) REFERENCES languages(bcp47);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_user_id FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_guide_language FOREIGN KEY (guide_language) REFERENCES languages(bcp47);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_preferred_currency FOREIGN KEY (preferred_currency) REFERENCES currencies(iso4217);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_max_daily_budget_currency FOREIGN KEY (max_daily_budget_currency) REFERENCES currencies(iso4217);
ALTER TABLE hotel_reviews ADD CONSTRAINT fk_hotel_reviews_hotel_id FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id);
ALTER TABLE hotel_reviews ADD CONSTRAINT fk_hotel_reviews_user_id FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE hotel_reviews ADD CONSTRAINT fk_hotel_reviews_language FOREIGN KEY (language) REFERENCES languages(bcp47);
ALTER TABLE hotel_reviews ADD CONSTRAINT fk_hotel_reviews_room_type_id FOREIGN KEY (room_type_id) REFERENCES hotel_room_types(room_type_id);

-- indexes
CREATE INDEX idx_categories_parent_category_id ON categories(parent_category_id);
CREATE INDEX idx_countries_default_currency ON countries(default_currency);
CREATE INDEX idx_cities_country_id ON cities(country_id);
CREATE INDEX idx_cities_primary_language ON cities(primary_language);
CREATE INDEX idx_hotels_city_id ON hotels(city_id);
CREATE INDEX idx_hotels_base_currency ON hotels(base_currency);
CREATE INDEX idx_tour_packages_city_id ON tour_packages(city_id);
CREATE INDEX idx_tour_packages_currency ON tour_packages(currency);
CREATE INDEX idx_users_home_city_id ON users(home_city_id);
CREATE INDEX idx_users_home_currency ON users(home_currency);
CREATE INDEX idx_users_locale ON users(locale);
CREATE INDEX idx_activities_poi_city_id ON activities_poi(city_id);
CREATE INDEX idx_activities_poi_category_id ON activities_poi(category_id);
CREATE INDEX idx_activities_poi_currency ON activities_poi(currency);
CREATE INDEX idx_eval_queries_language ON eval_queries(language);
CREATE INDEX idx_eval_queries_city_id ON eval_queries(city_id);
CREATE INDEX idx_eval_queries_persona_user_id ON eval_queries(persona_user_id);
CREATE INDEX idx_eval_relevance_labels_query_id ON eval_relevance_labels(query_id);
CREATE INDEX idx_hotel_room_types_hotel_id ON hotel_room_types(hotel_id);
CREATE INDEX idx_hotel_room_types_currency ON hotel_room_types(currency);
CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);
CREATE INDEX idx_user_interactions_query_language ON user_interactions(query_language);
CREATE INDEX idx_user_preferences_guide_language ON user_preferences(guide_language);
CREATE INDEX idx_user_preferences_preferred_currency ON user_preferences(preferred_currency);
CREATE INDEX idx_user_preferences_max_daily_budget_currency ON user_preferences(max_daily_budget_currency);
CREATE INDEX idx_hotel_reviews_hotel_id ON hotel_reviews(hotel_id);
CREATE INDEX idx_hotel_reviews_user_id ON hotel_reviews(user_id);
CREATE INDEX idx_hotel_reviews_language ON hotel_reviews(language);
CREATE INDEX idx_hotel_reviews_room_type_id ON hotel_reviews(room_type_id);