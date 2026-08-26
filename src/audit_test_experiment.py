from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_METHOD_SUFFIXES = {
    "BM25_top1": "bm25_top1",
    "BM25_top3": "bm25_top3",
    "BM25_top5": "bm25_top5",
    "BM25_top7": "bm25_top7",
    "BM25_top8": "bm25_top8",
    "BM25_top10": "bm25_top10",
    "BM25_top20": "bm25_top20",
    "ControllerV3": "controller_v3",
    "ControllerV3_no_section": "controller_v3_no_section",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit alignment, completeness, and hashes for a frozen test run."
    )
    parser.add_argument(
        "--input",
        default="data/processed/qasper_test_416.jsonl",
        help="Processed held-out test split.",
    )
    parser.add_argument("--output-dir", default="outputs/test416")
    parser.add_argument("--run-name", default="test416")
    parser.add_argument("--expected-papers", type=int, default=416)
    parser.add_argument("--expected-questions", type=int, default=1451)
    parser.add_argument("--expected-questions-with-gold", type=int, default=1352)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
    return records


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_keys(input_path: Path) -> tuple[set[tuple[str, str]], int]:
    records = read_jsonl(input_path)
    keys: list[tuple[str, str]] = []
    for paper in records:
        paper_id = str(paper["paper_id"])
        keys.extend(
            (paper_id, str(question["question_id"]))
            for question in paper.get("questions", [])
        )
    if len(keys) != len(set(keys)):
        raise ValueError("The processed test split contains duplicate question keys.")
    return set(keys), len(records)


def check_method_file(
    path: Path, canonical: set[tuple[str, str]]
) -> dict[str, Any]:
    records = read_jsonl(path)
    keys = [(str(row["paper_id"]), str(row["question_id"])) for row in records]
    key_set = set(keys)
    return {
        "path": str(path),
        "records": len(records),
        "papers": len({paper_id for paper_id, _ in keys}),
        "unique_keys": len(key_set),
        "duplicate_keys": len(keys) - len(key_set),
        "missing_keys": len(canonical - key_set),
        "unexpected_keys": len(key_set - canonical),
        "sha256": sha256(path),
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical, paper_count = canonical_keys(input_path)
    errors: list[str] = []
    if paper_count != args.expected_papers:
        errors.append(f"Expected {args.expected_papers} papers, found {paper_count}.")
    if len(canonical) != args.expected_questions:
        errors.append(
            f"Expected {args.expected_questions} questions, found {len(canonical)}."
        )

    methods: dict[str, dict[str, Any]] = {}
    for method, suffix in EXPECTED_METHOD_SUFFIXES.items():
        path = output_dir / f"{args.run_name}_{suffix}.jsonl"
        if not path.exists():
            errors.append(f"Missing method output: {path}")
            continue
        result = check_method_file(path, canonical)
        methods[method] = result
        if result["records"] != args.expected_questions:
            errors.append(f"{method} has {result['records']} records.")
        for field in ("duplicate_keys", "missing_keys", "unexpected_keys"):
            if result[field] != 0:
                errors.append(f"{method} has {result[field]} {field}.")

    summary_path = output_dir / f"{args.run_name}_method_comparison_threshold05.csv"
    if not summary_path.exists():
        errors.append(f"Missing method summary: {summary_path}")
        summary_rows: list[dict[str, str]] = []
    else:
        with summary_path.open("r", encoding="utf-8", newline="") as handle:
            summary_rows = list(csv.DictReader(handle))
        summary_methods = {row["method"] for row in summary_rows}
        if summary_methods != set(EXPECTED_METHOD_SUFFIXES):
            errors.append("Summary method set does not match the expected frozen methods.")
        gold_counts = {int(row["total_questions_with_gold"]) for row in summary_rows}
        if gold_counts != {args.expected_questions_with_gold}:
            errors.append(
                "Unexpected questions-with-gold count in the method summary: "
                f"{sorted(gold_counts)}"
            )

    bootstrap_config_path = output_dir / f"{args.run_name}_bootstrap_config.json"
    if not bootstrap_config_path.exists():
        errors.append(f"Missing bootstrap configuration: {bootstrap_config_path}")
        bootstrap_config: dict[str, Any] = {}
    else:
        bootstrap_config = json.loads(bootstrap_config_path.read_text(encoding="utf-8"))
        expected_bootstrap = {
            "replicates": 5000,
            "seed": 42,
            "resampling_unit": "paper",
        }
        for field, expected in expected_bootstrap.items():
            if bootstrap_config.get(field) != expected:
                errors.append(
                    f"Bootstrap {field} is {bootstrap_config.get(field)!r}; "
                    f"expected {expected!r}."
                )

    required_artifacts = [
        input_path,
        summary_path,
        output_dir / f"{args.run_name}_bootstrap_method_cis.csv",
        output_dir / f"{args.run_name}_bootstrap_paired_differences.csv",
        bootstrap_config_path,
        output_dir / f"{args.run_name}_error_analysis_controller_v3.csv",
        Path("src/build_evidence_units.py"),
        Path("src/run_retrieval_experiment.py"),
        Path("src/run_controller_v3.py"),
        Path("src/bootstrap_retrieval.py"),
    ]
    required_artifacts.extend(Path(result["path"]) for result in methods.values())

    manifest_rows = []
    for path in required_artifacts:
        if not path.exists():
            errors.append(f"Missing required artifact: {path}")
            continue
        manifest_rows.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    status = "pass" if not errors else "fail"
    audit = {
        "status": status,
        "run_name": args.run_name,
        "input": str(input_path),
        "input_sha256": sha256(input_path),
        "papers": paper_count,
        "questions": len(canonical),
        "questions_with_gold": (
            int(summary_rows[0]["total_questions_with_gold"]) if summary_rows else None
        ),
        "methods": methods,
        "bootstrap": bootstrap_config,
        "errors": errors,
    }

    audit_path = output_dir / f"{args.run_name}_audit.json"
    manifest_path = output_dir / f"{args.run_name}_sha256_manifest.csv"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Audit status: {status}")
    print(f"Papers: {paper_count}; questions: {len(canonical)}")
    print(f"Methods checked: {len(methods)}")
    print(f"Saved audit to {audit_path}")
    print(f"Saved SHA-256 manifest to {manifest_path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
