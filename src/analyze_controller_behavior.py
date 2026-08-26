from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from common import read_jsonl, write_csv
from retrieval import evaluate_predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descriptive variable-budget analysis for frozen ControllerV3."
    )
    parser.add_argument(
        "--controller", default="outputs/test416/test416_controller_v3.jsonl"
    )
    parser.add_argument(
        "--baseline", default="outputs/test416/test416_bm25_top7.jsonl"
    )
    parser.add_argument("--output-dir", default="outputs/supplementary")
    parser.add_argument("--run-name", default="test416_controller_behavior")
    parser.add_argument("--threshold", type=float, default=0.5)
    return parser.parse_args()


def keyed(records: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    result = {}
    for record in records:
        key = (str(record["paper_id"]), str(record["question_id"]))
        if key in result:
            raise ValueError(f"Duplicate key: {key}")
        result[key] = record
    return result


def unit_words(record: Dict[str, Any]) -> int:
    return sum(
        int(unit.get("word_count", len(unit.get("text", "").split())))
        for unit in record.get("retrieved_units", [])
    )


def path_name(record: Dict[str, Any]) -> str:
    question_type = record.get("question_type", {})
    if question_type.get("is_definition"):
        return "definition"
    if question_type.get("is_result") or question_type.get("is_data"):
        return "result_or_data"
    if question_type.get("is_method") or question_type.get("is_complex"):
        return "method_or_complex"
    return "default"


def distribution(values: List[float]) -> Dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "mean": round(float(array.mean()), 6),
        "sd": round(float(array.std(ddof=1)), 6) if array.size > 1 else 0.0,
        "median": round(float(np.median(array)), 6),
        "p10": round(float(np.percentile(array, 10)), 6),
        "p25": round(float(np.percentile(array, 25)), 6),
        "p75": round(float(np.percentile(array, 75)), 6),
        "p90": round(float(np.percentile(array, 90)), 6),
        "min": round(float(array.min()), 6),
        "max": round(float(array.max()), 6),
    }


def method_distribution(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    units = [len(record.get("retrieved_units", [])) for record in records]
    words = [unit_words(record) for record in records]
    tokens = [word * 1.3 for word in words]
    return {
        "retrieved_units": distribution(units),
        "evidence_words": distribution(words),
        "estimated_tokens_continuous": distribution(tokens),
    }


def main() -> None:
    args = parse_args()
    controller = read_jsonl(args.controller)
    baseline = read_jsonl(args.baseline)
    controller_by_key = keyed(controller)
    baseline_by_key = keyed(baseline)
    if set(controller_by_key) != set(baseline_by_key):
        raise ValueError("Controller and top-7 question keys do not align.")

    paired_rows = []
    relation_counts: Counter[str] = Counter()
    for key in sorted(controller_by_key):
        controller_record = controller_by_key[key]
        baseline_record = baseline_by_key[key]
        controller_tokens = unit_words(controller_record) * 1.3
        baseline_tokens = unit_words(baseline_record) * 1.3
        difference = controller_tokens - baseline_tokens
        relation = "lower" if difference < 0 else "higher" if difference > 0 else "equal"
        relation_counts[relation] += 1
        paired_rows.append(
            {
                "paper_id": key[0],
                "question_id": key[1],
                "decision_path": path_name(controller_record),
                "controller_units": len(controller_record.get("retrieved_units", [])),
                "top7_units": len(baseline_record.get("retrieved_units", [])),
                "controller_estimated_tokens": round(controller_tokens, 3),
                "top7_estimated_tokens": round(baseline_tokens, 3),
                "token_difference": round(difference, 3),
                "controller_budget_relation": relation,
            }
        )

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in controller:
        grouped[path_name(record)].append(record)

    path_rows = []
    for path in ("definition", "result_or_data", "method_or_complex", "default"):
        records = grouped.get(path, [])
        evaluation = evaluate_predictions(records, threshold=args.threshold)
        words = [unit_words(record) for record in records]
        tokens = [word * 1.3 for word in words]
        path_rows.append(
            {
                "decision_path": path,
                "questions": len(records),
                "questions_with_gold": evaluation["total_questions_with_gold"],
                "evidence_recall": round(evaluation["evidence_recall"], 6),
                "question_hit_rate": round(evaluation["question_hit_rate"], 6),
                "average_best_overlap": round(evaluation["average_best_overlap"], 6),
                "avg_retrieved_units": round(
                    statistics.mean(
                        len(record.get("retrieved_units", [])) for record in records
                    ),
                    6,
                )
                if records
                else 0.0,
                "avg_estimated_tokens": round(statistics.mean(tokens), 6)
                if tokens
                else 0.0,
                "median_estimated_tokens": round(statistics.median(tokens), 6)
                if tokens
                else 0.0,
            }
        )

    action_counts: Counter[str] = Counter()
    action_added: Counter[str] = Counter()
    sequence_counts: Counter[str] = Counter()
    selected_by_counts: Counter[str] = Counter()
    for record in controller:
        sequence = []
        for action in record.get("actions", []):
            name = action.get("action", "")
            sequence.append(name)
            action_counts[name] += 1
            action_added[name] += int(action.get("added_units", 0))
        sequence_counts[" -> ".join(sequence)] += 1
        for unit in record.get("retrieved_units", []):
            selected_by_counts[unit.get("selected_by", "")] += 1

    action_rows = [
        {
            "action": action,
            "trigger_count": count,
            "total_added_units": action_added[action],
            "avg_added_when_triggered": round(action_added[action] / count, 6),
        }
        for action, count in action_counts.most_common()
    ]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / args.run_name
    write_csv(paired_rows, f"{prefix}_paired_budget.csv")
    write_csv(path_rows, f"{prefix}_decision_paths.csv")
    write_csv(action_rows, f"{prefix}_actions.csv")

    total = len(paired_rows)
    summary = {
        "controller": method_distribution(controller),
        "bm25_top7": method_distribution(baseline),
        "paired_token_difference": distribution(
            [row["token_difference"] for row in paired_rows]
        ),
        "controller_budget_relation_to_top7": {
            relation: {
                "count": relation_counts[relation],
                "proportion": round(relation_counts[relation] / total, 6),
            }
            for relation in ("lower", "equal", "higher")
        },
        "decision_paths": path_rows,
        "action_counts": dict(action_counts),
        "action_added_units": dict(action_added),
        "action_sequence_counts": dict(sequence_counts),
        "selected_by_counts": dict(selected_by_counts),
        "interpretation_boundary": (
            "Decision-path results are post-primary descriptive/exploratory analyses."
        ),
    }
    Path(f"{prefix}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
