from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from bootstrap_retrieval import (
    aggregate_arrays,
    build_paper_aggregates,
    metric_arrays,
    percentile_interval,
    question_keys,
    sum_all,
    sum_selected,
)
from common import read_jsonl, write_csv


DEFAULT_METHOD_FILES = {
    "ControllerV3": "outputs/test416/test416_controller_v3.jsonl",
    "ControllerV3_no_section": "outputs/test416/test416_controller_v3_no_section.jsonl",
    "AbstractOnly": "outputs/supplementary/test416_supplementary_abstract_only.jsonl",
    "ReadAll": "outputs/supplementary/test416_supplementary_read_all.jsonl",
    "GenericCountMatched": "outputs/supplementary/test416_supplementary_generic_count_matched.jsonl",
    "GenericTokenMatched": "outputs/supplementary/test416_supplementary_generic_token_matched.jsonl",
}
DEFAULT_COMPARISONS = [
    ("ControllerV3", "GenericCountMatched"),
    ("ControllerV3", "GenericTokenMatched"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper-level bootstrap for supplementary retrieval controls."
    )
    parser.add_argument("--output-dir", default="outputs/supplementary")
    parser.add_argument("--run-name", default="test416_supplementary")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    method_files = {method: Path(path) for method, path in DEFAULT_METHOD_FILES.items()}
    missing = [str(path) for path in method_files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing method files: {missing}")

    records_by_method = {
        method: read_jsonl(str(path)) for method, path in method_files.items()
    }
    reference_method = "ControllerV3"
    reference_keys = question_keys(records_by_method[reference_method])
    for method, records in records_by_method.items():
        keys = question_keys(records)
        if len(keys) != len(records):
            raise ValueError(f"Duplicate paper/question keys in {method}.")
        if keys != reference_keys:
            raise ValueError(f"Question alignment differs for {method}.")

    thresholds = [args.threshold]
    paper_aggregates = {
        method: build_paper_aggregates(records, thresholds)
        for method, records in records_by_method.items()
    }
    paper_ids = sorted(paper_aggregates[reference_method])
    arrays_by_method = {
        method: aggregate_arrays(rows, paper_ids)
        for method, rows in paper_aggregates.items()
    }
    rng = np.random.default_rng(args.seed)
    indices = rng.integers(
        0, len(paper_ids), size=(args.replicates, len(paper_ids))
    )

    points: Dict[str, Dict[float, Dict[str, np.ndarray]]] = {}
    samples: Dict[str, Dict[float, Dict[str, np.ndarray]]] = {}
    method_rows: List[Dict[str, Any]] = []
    for method, arrays in arrays_by_method.items():
        points[method] = metric_arrays(sum_all(arrays), thresholds)
        samples[method] = metric_arrays(sum_selected(arrays, indices), thresholds)
        for metric, values in samples[method][args.threshold].items():
            lower, upper = percentile_interval(values)
            method_rows.append(
                {
                    "method": method,
                    "threshold": args.threshold,
                    "metric": metric,
                    "point_estimate": round(
                        float(points[method][args.threshold][metric][0]), 6
                    ),
                    "ci_lower": round(lower, 6),
                    "ci_upper": round(upper, 6),
                    "papers": len(paper_ids),
                    "replicates": args.replicates,
                    "seed": args.seed,
                    "resampling_unit": "paper",
                }
            )

    paired_rows: List[Dict[str, Any]] = []
    for first, second in DEFAULT_COMPARISONS:
        for metric in samples[first][args.threshold]:
            differences = (
                samples[first][args.threshold][metric]
                - samples[second][args.threshold][metric]
            )
            lower, upper = percentile_interval(differences)
            point = (
                float(points[first][args.threshold][metric][0])
                - float(points[second][args.threshold][metric][0])
            )
            paired_rows.append(
                {
                    "first_method": first,
                    "second_method": second,
                    "contrast": f"{first} - {second}",
                    "threshold": args.threshold,
                    "metric": metric,
                    "point_difference": round(point, 6),
                    "ci_lower": round(lower, 6),
                    "ci_upper": round(upper, 6),
                    "papers": len(paper_ids),
                    "replicates": args.replicates,
                    "seed": args.seed,
                    "resampling_unit": "paper",
                }
            )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / args.run_name
    write_csv(method_rows, f"{prefix}_bootstrap_method_cis.csv")
    write_csv(paired_rows, f"{prefix}_bootstrap_paired_differences.csv")
    config = {
        "method_files": {method: str(path) for method, path in method_files.items()},
        "comparisons": DEFAULT_COMPARISONS,
        "threshold": args.threshold,
        "papers": len(paper_ids),
        "questions": len(reference_keys),
        "replicates": args.replicates,
        "seed": args.seed,
        "resampling_unit": "paper",
        "ci_method": "percentile paired cluster bootstrap",
    }
    Path(f"{prefix}_bootstrap_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
