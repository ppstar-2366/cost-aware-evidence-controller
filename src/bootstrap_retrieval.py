import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from common import read_jsonl, write_csv
from retrieval import best_overlap_for_gold


DEFAULT_THRESHOLDS = [0.3, 0.5, 0.7]
DEFAULT_COMPARISONS = [
    ("ControllerV3", "BM25_top5"),
    ("ControllerV3", "BM25_top7"),
    ("ControllerV3", "BM25_top8"),
    ("ControllerV3", "BM25_top10"),
    ("ControllerV3", "ControllerV3_no_section"),
]


def threshold_key(threshold: float) -> str:
    return f"{threshold:g}".replace(".", "p")


def method_name(path: Path, run_name: str) -> str:
    stem = path.stem
    prefix = f"{run_name}_"
    if not stem.startswith(prefix):
        raise ValueError(f"Unexpected artifact name: {path}")

    suffix = stem[len(prefix):]
    if suffix.startswith("bm25_top"):
        return f"BM25_top{suffix.removeprefix('bm25_top')}"
    if suffix == "controller_v3":
        return "ControllerV3"
    if suffix == "controller_v3_no_section":
        return "ControllerV3_no_section"
    raise ValueError(f"Cannot infer method name from {path}")


def discover_method_files(output_dir: Path, run_name: str) -> Dict[str, Path]:
    candidates = list(output_dir.glob(f"{run_name}_bm25_top*.jsonl"))
    candidates.extend(
        path
        for path in [
            output_dir / f"{run_name}_controller_v3.jsonl",
            output_dir / f"{run_name}_controller_v3_no_section.jsonl",
        ]
        if path.exists()
    )

    files = {method_name(path, run_name): path for path in candidates}
    if not files:
        raise FileNotFoundError(
            f"No retrieval artifacts found for run '{run_name}' in {output_dir}"
        )
    return files


def question_keys(records: Iterable[Dict[str, Any]]) -> set[Tuple[str, str]]:
    return {
        (str(record.get("paper_id", "")), str(record.get("question_id", "")))
        for record in records
    }


def build_paper_aggregates(
    records: List[Dict[str, Any]],
    thresholds: List[float],
) -> Dict[str, Dict[str, float]]:
    by_paper: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_paper[str(record["paper_id"])].append(record)

    aggregates: Dict[str, Dict[str, float]] = {}
    for paper_id, items in by_paper.items():
        row: Dict[str, float] = {
            "question_count": float(len(items)),
            "gold_question_count": 0.0,
            "gold_span_count": 0.0,
            "sum_best_overlap": 0.0,
            "total_words": 0.0,
            "total_units": 0.0,
        }
        for threshold in thresholds:
            key = threshold_key(threshold)
            row[f"covered_gold_{key}"] = 0.0
            row[f"hit_questions_{key}"] = 0.0

        for item in items:
            retrieved_units = item.get("retrieved_units", [])
            gold_evidence = item.get("gold_evidence", [])
            row["total_units"] += len(retrieved_units)
            row["total_words"] += sum(
                float(unit.get("word_count", len(unit.get("text", "").split())))
                for unit in retrieved_units
            )

            if not gold_evidence:
                continue

            row["gold_question_count"] += 1.0
            best_scores = [
                best_overlap_for_gold(gold, retrieved_units)
                for gold in gold_evidence
            ]
            row["gold_span_count"] += len(best_scores)
            row["sum_best_overlap"] += sum(best_scores)

            for threshold in thresholds:
                key = threshold_key(threshold)
                row[f"covered_gold_{key}"] += sum(
                    score >= threshold for score in best_scores
                )
                row[f"hit_questions_{key}"] += float(
                    any(score >= threshold for score in best_scores)
                )

        aggregates[paper_id] = row

    return aggregates


def safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def metric_arrays(
    summed: Dict[str, np.ndarray],
    thresholds: List[float],
) -> Dict[float, Dict[str, np.ndarray]]:
    avg_words = safe_divide(summed["total_words"], summed["question_count"])
    avg_tokens = avg_words * 1.3
    avg_units = safe_divide(summed["total_units"], summed["question_count"])
    avg_best_overlap = safe_divide(
        summed["sum_best_overlap"], summed["gold_span_count"]
    )

    result: Dict[float, Dict[str, np.ndarray]] = {}
    for threshold in thresholds:
        key = threshold_key(threshold)
        recall = safe_divide(
            summed[f"covered_gold_{key}"], summed["gold_span_count"]
        )
        hit_rate = safe_divide(
            summed[f"hit_questions_{key}"], summed["gold_question_count"]
        )
        recall_per_1k = safe_divide(recall * 1000.0, avg_tokens)
        result[threshold] = {
            "evidence_recall": recall,
            "question_hit_rate": hit_rate,
            "average_best_overlap": avg_best_overlap,
            "avg_estimated_tokens": avg_tokens,
            "avg_retrieved_units": avg_units,
            "recall_per_1k_tokens": recall_per_1k,
        }
    return result


def aggregate_arrays(
    paper_rows: Dict[str, Dict[str, float]],
    paper_ids: List[str],
) -> Dict[str, np.ndarray]:
    columns = list(next(iter(paper_rows.values())).keys())
    return {
        column: np.array([paper_rows[paper_id][column] for paper_id in paper_ids])
        for column in columns
    }


def sum_selected(
    arrays: Dict[str, np.ndarray],
    indices: np.ndarray,
) -> Dict[str, np.ndarray]:
    return {column: values[indices].sum(axis=1) for column, values in arrays.items()}


def sum_all(arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    return {
        column: np.array([values.sum()], dtype=float)
        for column, values in arrays.items()
    }


def percentile_interval(values: np.ndarray) -> Tuple[float, float]:
    lower, upper = np.percentile(values, [2.5, 97.5])
    return float(lower), float(upper)


def parse_comparison(value: str) -> Tuple[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError(
            "Comparisons must use FIRST:SECOND format."
        )
    first, second = value.split(":", 1)
    return first, second


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper-level paired bootstrap for retrieval experiments."
    )
    parser.add_argument("--output-dir", default="outputs/test416")
    parser.add_argument("--run-name", default="test416")
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_THRESHOLDS,
    )
    parser.add_argument(
        "--comparison",
        type=parse_comparison,
        action="append",
        help="Paired difference in FIRST:SECOND format. Repeat as needed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    method_files = discover_method_files(output_dir, args.run_name)
    comparisons = args.comparison or DEFAULT_COMPARISONS

    records_by_method = {
        method: read_jsonl(str(path)) for method, path in method_files.items()
    }
    reference_method = sorted(records_by_method)[0]
    reference_keys = question_keys(records_by_method[reference_method])
    if len(reference_keys) != len(records_by_method[reference_method]):
        raise ValueError(f"Duplicate paper/question keys in {reference_method}")

    for method, records in records_by_method.items():
        keys = question_keys(records)
        if len(keys) != len(records):
            raise ValueError(f"Duplicate paper/question keys in {method}")
        if keys != reference_keys:
            raise ValueError(f"Question alignment differs for {method}")

    paper_aggregates = {
        method: build_paper_aggregates(records, args.thresholds)
        for method, records in records_by_method.items()
    }
    paper_ids = sorted(paper_aggregates[reference_method])
    for method, rows in paper_aggregates.items():
        if set(rows) != set(paper_ids):
            raise ValueError(f"Paper alignment differs for {method}")

    arrays_by_method = {
        method: aggregate_arrays(rows, paper_ids)
        for method, rows in paper_aggregates.items()
    }

    rng = np.random.default_rng(args.seed)
    sample_indices = rng.integers(
        0,
        len(paper_ids),
        size=(args.replicates, len(paper_ids)),
    )

    points: Dict[str, Dict[float, Dict[str, np.ndarray]]] = {}
    samples: Dict[str, Dict[float, Dict[str, np.ndarray]]] = {}
    method_rows: List[Dict[str, Any]] = []

    for method, arrays in arrays_by_method.items():
        points[method] = metric_arrays(sum_all(arrays), args.thresholds)
        samples[method] = metric_arrays(
            sum_selected(arrays, sample_indices), args.thresholds
        )

        for threshold in args.thresholds:
            for metric, values in samples[method][threshold].items():
                lower, upper = percentile_interval(values)
                method_rows.append(
                    {
                        "method": method,
                        "threshold": threshold,
                        "metric": metric,
                        "point_estimate": round(
                            float(points[method][threshold][metric][0]), 6
                        ),
                        "ci_lower": round(lower, 6),
                        "ci_upper": round(upper, 6),
                        "confidence_level": 0.95,
                        "ci_method": "percentile_cluster_bootstrap",
                        "resampling_unit": "paper",
                        "papers": len(paper_ids),
                        "replicates": args.replicates,
                        "seed": args.seed,
                    }
                )

    paired_rows: List[Dict[str, Any]] = []
    for first, second in comparisons:
        if first not in samples or second not in samples:
            raise ValueError(
                f"Missing comparison method: {first}:{second}. "
                f"Available methods: {sorted(samples)}"
            )

        for threshold in args.thresholds:
            for metric in samples[first][threshold]:
                differences = (
                    samples[first][threshold][metric]
                    - samples[second][threshold][metric]
                )
                point_difference = (
                    float(points[first][threshold][metric][0])
                    - float(points[second][threshold][metric][0])
                )
                lower, upper = percentile_interval(differences)
                paired_rows.append(
                    {
                        "first_method": first,
                        "second_method": second,
                        "contrast": f"{first} - {second}",
                        "threshold": threshold,
                        "metric": metric,
                        "point_difference": round(point_difference, 6),
                        "ci_lower": round(lower, 6),
                        "ci_upper": round(upper, 6),
                        "confidence_level": 0.95,
                        "ci_method": "percentile_paired_cluster_bootstrap",
                        "resampling_unit": "paper",
                        "papers": len(paper_ids),
                        "replicates": args.replicates,
                        "seed": args.seed,
                    }
                )

    method_output = output_dir / f"{args.run_name}_bootstrap_method_cis.csv"
    paired_output = output_dir / f"{args.run_name}_bootstrap_paired_differences.csv"
    config_output = output_dir / f"{args.run_name}_bootstrap_config.json"
    write_csv(method_rows, str(method_output))
    write_csv(paired_rows, str(paired_output))

    config = {
        "run_name": args.run_name,
        "method_files": {
            method: str(path) for method, path in sorted(method_files.items())
        },
        "paper_count": len(paper_ids),
        "question_count": len(reference_keys),
        "thresholds": args.thresholds,
        "comparisons": [list(pair) for pair in comparisons],
        "replicates": args.replicates,
        "seed": args.seed,
        "confidence_level": 0.95,
        "ci_method": "percentile paired cluster bootstrap",
        "resampling_unit": "paper",
    }
    config_output.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Methods: {', '.join(sorted(method_files))}")
    print(f"Papers: {len(paper_ids)}; questions: {len(reference_keys)}")
    print(f"Saved method intervals to {method_output}")
    print(f"Saved paired differences to {paired_output}")
    print(f"Saved bootstrap configuration to {config_output}")


if __name__ == "__main__":
    main()
