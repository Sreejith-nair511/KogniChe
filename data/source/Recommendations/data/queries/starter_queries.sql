-- APS-04 — Hyper-Personalized Recommendation Engine
-- Starter queries. Every one runs as-is against data/APS-04.db.
--
-- CAST(x AS REAL) appears below only for sorting and rough exploration.
-- Never use it for a value you will show someone or add to another value.

-- ==========================================================================
-- 1. The three cohorts — and the cold-start one really is cold
-- F2. If every user has history, cold start is untestable.
-- ==========================================================================
SELECT u.segment, COUNT(DISTINCT u.user_id) AS users,
          COUNT(i.interaction_id) AS interactions,
          ROUND(1.0*COUNT(i.interaction_id)/COUNT(DISTINCT u.user_id),1) AS per_user
     FROM users u LEFT JOIN user_interactions i ON i.user_id = u.user_id
    GROUP BY u.segment;

-- ==========================================================================
-- 2. One heavy user's full history — the profile you personalise from
-- position_in_list is here so your offline evaluation can debias.
-- ==========================================================================
SELECT i.occurred_at, i.entity_type, i.interaction_type, i.dwell_seconds,
          i.position_in_list, i.implicit_rating, i.channel
     FROM user_interactions i
    WHERE i.user_id = (SELECT user_id FROM users WHERE segment='heavy' ORDER BY user_id LIMIT 1)
    ORDER BY i.occurred_at DESC LIMIT 25;

-- ==========================================================================
-- 3. The shared evaluation set — 120 queries, including Hindi and Tamil
-- F6. A number computed on your own private labels is not a number anyone can compare.
-- ==========================================================================
SELECT query_id, language, intent, target_entity_type, k, query_text
     FROM eval_queries ORDER BY language, intent LIMIT 20;

-- ==========================================================================
-- 4. Graded relevance for one query
-- 0 irrelevant, 1 marginal, 2 relevant, 3 ideal. This is your ground truth.
-- ==========================================================================
SELECT l.grade, COUNT(*) AS candidates
     FROM eval_relevance_labels l
    WHERE l.query_id = (SELECT query_id FROM eval_queries ORDER BY query_id LIMIT 1)
    GROUP BY l.grade ORDER BY l.grade DESC;

-- ==========================================================================
-- 5. A precision@k skeleton you can adapt
-- Replace the inner SELECT with your ranked results and this becomes your metric.
-- ==========================================================================
WITH ranked AS (
       SELECT l.query_id, l.entity_id, l.grade,
              ROW_NUMBER() OVER (PARTITION BY l.query_id ORDER BY l.grade DESC, l.entity_id) AS rnk
         FROM eval_relevance_labels l)
     SELECT query_id,
            ROUND(1.0*SUM(CASE WHEN grade >= 2 THEN 1 ELSE 0 END)/10.0, 3) AS precision_at_10
       FROM ranked WHERE rnk <= 10 GROUP BY query_id LIMIT 10;

-- ==========================================================================
-- 6. Multilingual content to retrieve over
-- Queries come in ta and hi. Your retriever has to cope with mixed-script content.
-- ==========================================================================
SELECT language, COUNT(*) AS reviews FROM hotel_reviews GROUP BY language
    UNION ALL SELECT 'eval_queries:'||language, COUNT(*) FROM eval_queries GROUP BY language;
