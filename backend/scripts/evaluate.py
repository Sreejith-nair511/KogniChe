"""
Offline Evaluation Script — APS-04
Runs all four models against the real evaluation queries and relevance labels.
Reports honest metrics. Never manipulates results.
"""
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.evaluator import run_evaluation, run_full_comparison, get_failure_cases
from app.evaluation.metrics import load_eval_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def print_metrics(name: str, metrics):
    logger.info(f"\n  {name}:")
    logger.info(f"    Precision@5:  {metrics.precision_at_5:.4f}")
    logger.info(f"    Precision@10: {metrics.precision_at_10:.4f}")
    logger.info(f"    NDCG@5:       {metrics.ndcg_at_5:.4f}")
    logger.info(f"    NDCG@10:      {metrics.ndcg_at_10:.4f}")
    logger.info(f"    Recall@10:    {metrics.recall_at_10:.4f}")
    logger.info(f"    MRR:          {metrics.mrr:.4f}")
    logger.info(f"    Queries:      {metrics.num_queries}")


def run():
    logger.info("=" * 60)
    logger.info("NEXORA Offline Evaluation")
    logger.info("Using APS-04 eval_queries + eval_relevance_labels as ground truth")
    logger.info("=" * 60)

    # Load eval data info
    eval_data = load_eval_data()
    supported = [q for q in eval_data if q["target_entity_type"] in ("hotel", "poi", "package")]
    logger.info(f"\nEvaluation set: {len(eval_data)} total queries, {len(supported)} supported (hotel/poi/package)")
    lang_counts = {}
    for q in supported:
        lang_counts[q["language"]] = lang_counts.get(q["language"], 0) + 1
    for lang, cnt in sorted(lang_counts.items()):
        logger.info(f"  Language {lang}: {cnt} queries")

    max_q = min(len(supported), 60)  # cap for speed; remove to run all
    logger.info(f"\nRunning on {max_q} queries per model (of {len(supported)} supported)...")
    logger.info("This may take a few minutes on first run (embedding model warm-up).\n")

    # Popularity baseline
    logger.info("--- Running: Popularity Baseline ---")
    pop_m, _ = run_evaluation("popularity", max_queries=max_q)
    print_metrics("Popularity", pop_m)

    # Semantic baseline
    logger.info("\n--- Running: Semantic Retrieval ---")
    sem_m, _ = run_evaluation("semantic", max_queries=max_q)
    print_metrics("Semantic", sem_m)

    # Hybrid
    logger.info("\n--- Running: Hybrid Retrieval ---")
    hyb_m, _ = run_evaluation("hybrid", max_queries=max_q)
    print_metrics("Hybrid", hyb_m)

    # NEXORA
    logger.info("\n--- Running: NEXORA (Full Pipeline) ---")
    nex_m, nex_per_query = run_evaluation("nexora", max_queries=max_q)
    print_metrics("NEXORA", nex_m)

    # Summary table
    logger.info("\n" + "=" * 60)
    logger.info("MODEL COMPARISON SUMMARY")
    logger.info("=" * 60)
    logger.info(f"{'Model':<20} {'P@5':>8} {'P@10':>8} {'NDCG@5':>8} {'NDCG@10':>8} {'R@10':>8} {'MRR':>8}")
    logger.info("-" * 68)
    for name, m in [("Popularity", pop_m), ("Semantic", sem_m), ("Hybrid", hyb_m), ("NEXORA", nex_m)]:
        logger.info(
            f"{name:<20} {m.precision_at_5:>8.4f} {m.precision_at_10:>8.4f} "
            f"{m.ndcg_at_5:>8.4f} {m.ndcg_at_10:>8.4f} "
            f"{m.recall_at_10:>8.4f} {m.mrr:>8.4f}"
        )

    # Failure analysis
    logger.info("\n--- NEXORA Failure Analysis (worst 5 queries) ---")
    failures = get_failure_cases("nexora", max_queries=max_q, n=5)
    for f in failures:
        logger.info(f"  [{f['language']}] {f['query_text'][:60]}")
        logger.info(f"    Intent: {f['intent']} | NDCG@10={f['metric']:.4f}")
        logger.info(f"    Reason: {f['possible_reason']}")

    # Save results
    output_path = Path(__file__).parent.parent.parent / "docs" / "eval_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = {
        "models": {
            "popularity": pop_m.model_dump(),
            "semantic": sem_m.model_dump(),
            "hybrid": hyb_m.model_dump(),
            "nexora": nex_m.model_dump(),
        },
        "eval_set_size": max_q,
        "total_queries": len(eval_data),
        "languages": lang_counts,
    }
    output_path.write_text(json.dumps(results, indent=2))
    logger.info(f"\nResults saved to: {output_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
