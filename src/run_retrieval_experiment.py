import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from common import read_jsonl, write_csv, write_jsonl
from retrieval import compute_cost_stats, evaluate_predictions, overlap_score, run_bm25
from run_controller_v3 import run_controller_v3


DEFAULT_INPUT = "data/processed/qasper_validation_50.jsonl"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_TOP_K = [1, 3, 5, 10, 20]
DEFAULT_THRESHOLD = 0.5


def add_efficiency(row: Dict[str, Any]) -> Dict[str, Any]:
    recall = float(row["evidence_recall"])
    tokens = float(row["avg_estimated_tokens"])
    row["recall_per_1k_tokens"] = round(recall / tokens * 1000, 4) if tokens > 0 else 0
    return row


def make_summary_row(
    method: str,
    eval_stats: Dict[str, Any],
    cost_stats: Dict[str, Any],
    threshold: float,
) -> Dict[str, Any]:
    return add_efficiency(
        {
            "method": method,
            "threshold": threshold,
            "total_questions_with_gold": eval_stats["total_questions_with_gold"],
            "question_hit_rate": round(eval_stats["question_hit_rate"], 4),
            "evidence_recall": round(eval_stats["evidence_recall"], 4),
            "average_best_overlap": round(eval_stats["average_best_overlap"], 4),
            "avg_retrieved_units": cost_stats["avg_retrieved_units"],
            "avg_evidence_words": cost_stats["avg_evidence_words"],
            "avg_estimated_tokens": cost_stats["avg_estimated_tokens"],
            "avg_chunks": cost_stats["avg_chunks"],
            "avg_tables": cost_stats["avg_tables"],
            "avg_figures": cost_stats["avg_figures"],
            "avg_abstracts": cost_stats["avg_abstracts"],
            "avg_action_steps": cost_stats["avg_action_steps"],
        }
    )


def best_match(gold_evidence: List[str], retrieved_units: List[Dict[str, Any]]) -> Dict[str, Any]:
    best = {
        "best_score": 0.0,
        "best_gold": "",
        "best_unit_id": "",
        "best_unit_type": "",
        "best_section": "",
        "best_text": "",
    }

    for gold in gold_evidence:
        for unit in retrieved_units:
            score = overlap_score(gold, unit.get("text", ""))
            if score > best["best_score"]:
                best = {
                    "best_score": score,
                    "best_gold": gold,
                    "best_unit_id": unit.get("unit_id", ""),
                    "best_unit_type": unit.get("unit_type", ""),
                    "best_section": unit.get("section_name", ""),
                    "best_text": unit.get("text", ""),
                }

    return best


def action_sequence(item: Dict[str, Any]) -> str:
    return " -> ".join(action.get("action", "") for action in item.get("actions", []))


def selected_types(item: Dict[str, Any]) -> str:
    counter = Counter(unit.get("unit_type", "") for unit in item.get("retrieved_units", []))
    return "; ".join(f"{unit_type}:{count}" for unit_type, count in counter.items())


def classify_failure(
    controller_hit: bool,
    bm25_top20_hit: bool,
    actions: str,
    types: str,
    question: str,
) -> str:
    if controller_hit:
        return "success"

    if not bm25_top20_hit:
        return "retrieval_or_gold_mapping_failure"

    q = question.lower()

    if "ReadTop3 -> Stop" in actions:
        return "early_stop_failure"

    if any(word in q for word in ["dataset", "datasets", "corpus", "language", "languages", "data"]):
        return "data_evidence_selection_failure"

    if any(word in q for word in ["result", "accuracy", "score", "performance", "table"]):
        return "missing_table_failure" if "table" not in types else "result_evidence_selection_failure"

    if any(word in q for word in ["figure", "architecture", "pipeline", "diagram"]):
        return "missing_figure_failure" if "figure_caption" not in types else "figure_selection_failure"

    if any(word in q for word in ["what is", "what are", "what does", "abbreviate", "stand for"]):
        return "definition_selection_failure"

    return "controller_selection_failure"


def write_error_analysis(
    controller_path: str,
    bm25_top20_path: str,
    output_path: str,
    threshold: float,
) -> None:
    controller_items = read_jsonl(controller_path)
    bm25_items = read_jsonl(bm25_top20_path)
    bm25_by_qid = {item["question_id"]: item for item in bm25_items}

    rows = []
    category_counter: Counter = Counter()

    for item in controller_items:
        gold_evidence = item.get("gold_evidence", [])
        if not gold_evidence:
            continue

        bm25_item = bm25_by_qid.get(item["question_id"])
        if bm25_item is None:
            continue

        controller_match = best_match(gold_evidence, item.get("retrieved_units", []))
        bm25_match = best_match(gold_evidence, bm25_item.get("retrieved_units", []))

        controller_hit = controller_match["best_score"] >= threshold
        bm25_top20_hit = bm25_match["best_score"] >= threshold
        actions = action_sequence(item)
        types = selected_types(item)
        category = classify_failure(controller_hit, bm25_top20_hit, actions, types, item["question"])
        category_counter[category] += 1

        rows.append(
            {
                "paper_id": item["paper_id"],
                "question_id": item["question_id"],
                "question": item["question"],
                "category": category,
                "controller_hit": controller_hit,
                "controller_best_overlap": round(controller_match["best_score"], 4),
                "bm25_top20_hit": bm25_top20_hit,
                "bm25_top20_best_overlap": round(bm25_match["best_score"], 4),
                "action_sequence": actions,
                "selected_types": types,
                "gold_evidence_preview": controller_match["best_gold"][:350],
                "controller_best_unit_type": controller_match["best_unit_type"],
                "controller_best_section": controller_match["best_section"],
                "controller_best_text_preview": controller_match["best_text"][:350],
                "bm25_best_unit_type": bm25_match["best_unit_type"],
                "bm25_best_section": bm25_match["best_section"],
                "bm25_best_text_preview": bm25_match["best_text"][:350],
            }
        )

    write_csv(rows, output_path)

    print("\nError analysis category counts:")
    for category, count in category_counter.most_common():
        print(f"  {category}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BM25 baselines and the final cost-aware ControllerV3.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-name",
        default="validation50",
        help="Prefix used for every output artifact, for example test416.",
    )
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--top-k", type=int, nargs="+", default=DEFAULT_TOP_K)
    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Do not run the ControllerV3 no-section-expansion ablation.",
    )
    parser.add_argument("--skip-error-analysis", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: List[Dict[str, Any]] = []
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_prefix = output_dir / args.run_name

    print("\nRunning BM25 baselines...")
    for top_k in args.top_k:
        predictions = run_bm25(input_path=args.input, top_k=top_k)
        output_path = f"{artifact_prefix}_bm25_top{top_k}.jsonl"
        write_jsonl(predictions, output_path)

        rows.append(
            make_summary_row(
                method=f"BM25_top{top_k}",
                eval_stats=evaluate_predictions(predictions, threshold=args.threshold),
                cost_stats=compute_cost_stats(predictions),
                threshold=args.threshold,
            )
        )

    print("\nRunning ControllerV3...")
    controller_predictions = run_controller_v3(args.input)
    controller_path = f"{artifact_prefix}_controller_v3.jsonl"
    write_jsonl(controller_predictions, controller_path)

    rows.append(
        make_summary_row(
            method="ControllerV3",
            eval_stats=evaluate_predictions(controller_predictions, threshold=args.threshold),
            cost_stats=compute_cost_stats(controller_predictions),
            threshold=args.threshold,
        )
    )

    if not args.skip_ablation:
        print("\nRunning ControllerV3 ablation: no section-aware expansion...")
        ablation_predictions = run_controller_v3(
            args.input,
            use_section_expansion=False,
        )
        ablation_path = f"{artifact_prefix}_controller_v3_no_section.jsonl"
        write_jsonl(ablation_predictions, ablation_path)

        rows.append(
            make_summary_row(
                method="ControllerV3_no_section",
                eval_stats=evaluate_predictions(ablation_predictions, threshold=args.threshold),
                cost_stats=compute_cost_stats(ablation_predictions),
                threshold=args.threshold,
            )
        )

    threshold_label = f"{args.threshold:g}".replace(".", "")
    summary_path = f"{artifact_prefix}_method_comparison_threshold{threshold_label}.csv"
    write_csv(rows, summary_path)

    print("\nRetrieval comparison")
    print("=" * 96)
    for row in rows:
        print(
            f"{row['method']:16s} | "
            f"Recall={row['evidence_recall']:<6} | "
            f"Hit={row['question_hit_rate']:<6} | "
            f"Tokens={row['avg_estimated_tokens']:<6} | "
            f"Recall/1k={row['recall_per_1k_tokens']}"
        )

    print(f"\nSaved retrieval summary to {summary_path}")

    if not args.skip_error_analysis and 20 in args.top_k:
        error_path = f"{artifact_prefix}_error_analysis_controller_v3.csv"
        write_error_analysis(
            controller_path=controller_path,
            bm25_top20_path=f"{artifact_prefix}_bm25_top20.jsonl",
            output_path=error_path,
            threshold=args.threshold,
        )
        print(f"Saved error analysis to {error_path}")


if __name__ == "__main__":
    main()
