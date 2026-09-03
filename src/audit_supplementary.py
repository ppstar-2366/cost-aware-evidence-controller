from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD_SUFFIXES = {
    "AbstractOnly": "abstract_only",
    "ReadAll": "read_all",
    "GenericCountMatched": "generic_count_matched",
    "GenericTokenMatched": "generic_token_matched",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the frozen supplementary QASPER test analyses."
    )
    parser.add_argument("--input", default="data/processed/qasper_test_416.jsonl")
    parser.add_argument("--primary-dir", default="outputs/test416")
    parser.add_argument("--output-dir", default="outputs/supplementary")
    parser.add_argument("--run-name", default="test416_supplementary")
    parser.add_argument("--expected-papers", type=int, default=416)
    parser.add_argument("--expected-questions", type=int, default=1451)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
    return records


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def keys_from_processed(path: Path) -> tuple[set[tuple[str, str]], int]:
    papers = read_jsonl(path)
    keys = {
        (str(paper["paper_id"]), str(question["question_id"]))
        for paper in papers
        for question in paper.get("questions", [])
    }
    return keys, len(papers)


def method_check(path: Path, expected_keys: set[tuple[str, str]]) -> dict[str, Any]:
    records = read_jsonl(path)
    keys = [(str(row["paper_id"]), str(row["question_id"])) for row in records]
    unique_keys = set(keys)
    return {
        "path": str(path),
        "records": len(records),
        "papers": len({paper_id for paper_id, _ in keys}),
        "unique_keys": len(unique_keys),
        "duplicate_keys": len(keys) - len(unique_keys),
        "missing_keys": len(expected_keys - unique_keys),
        "unexpected_keys": len(unique_keys - expected_keys),
        "sha256": sha256(path),
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    primary_dir = Path(args.primary_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    expected_keys, paper_count = keys_from_processed(input_path)
    errors: list[str] = []
    if paper_count != args.expected_papers:
        errors.append(f"Expected {args.expected_papers} papers; found {paper_count}.")
    if len(expected_keys) != args.expected_questions:
        errors.append(
            f"Expected {args.expected_questions} questions; found {len(expected_keys)}."
        )

    methods: dict[str, dict[str, Any]] = {}
    for method, suffix in METHOD_SUFFIXES.items():
        path = output_dir / f"{args.run_name}_{suffix}.jsonl"
        if not path.exists():
            errors.append(f"Missing method output: {path}")
            continue
        result = method_check(path, expected_keys)
        methods[method] = result
        if result["records"] != args.expected_questions:
            errors.append(f"{method} has {result['records']} records.")
        for field in ("duplicate_keys", "missing_keys", "unexpected_keys"):
            if result[field] != 0:
                errors.append(f"{method} has {result[field]} {field}.")

    budget_path = output_dir / f"{args.run_name}_budget_match_details.csv"
    budget_rows = read_csv(budget_path)
    count_differences = [abs(int(row["count_unit_difference"])) for row in budget_rows]
    token_differences = [abs(int(row["token_word_difference"])) for row in budget_rows]
    if len(budget_rows) != args.expected_questions:
        errors.append(f"Budget audit has {len(budget_rows)} rows.")
    if count_differences and max(count_differences) != 0:
        errors.append("GenericCountMatched does not exactly match all unit counts.")

    behavior_path = output_dir / "test416_controller_behavior_paired_budget.csv"
    behavior_rows = read_csv(behavior_path)
    if len(behavior_rows) != args.expected_questions:
        errors.append(f"Behaviour audit has {len(behavior_rows)} paired rows.")
    path_rows = read_csv(
        output_dir / "test416_controller_behavior_decision_paths.csv"
    )
    path_total = sum(int(row["questions"]) for row in path_rows)
    if path_total != args.expected_questions:
        errors.append(f"Decision paths sum to {path_total} questions.")

    bootstrap_path = output_dir / f"{args.run_name}_bootstrap_config.json"
    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    for field, expected in {
        "replicates": 5000,
        "seed": 42,
        "resampling_unit": "paper",
        "threshold": 0.5,
    }.items():
        if bootstrap.get(field) != expected:
            errors.append(
                f"Bootstrap {field} is {bootstrap.get(field)!r}; expected {expected!r}."
            )

    primary_paths = [
        primary_dir / "test416_controller_v3.jsonl",
        primary_dir / "test416_controller_v3_no_section.jsonl",
        primary_dir / "test416_bm25_top7.jsonl",
    ]
    summary_paths = [
        output_dir / f"{args.run_name}_retrieval_summary.csv",
        output_dir / f"{args.run_name}_bootstrap_method_cis.csv",
        output_dir / f"{args.run_name}_bootstrap_paired_differences.csv",
        bootstrap_path,
        budget_path,
        output_dir / "test416_controller_behavior_actions.csv",
        output_dir / "test416_controller_behavior_decision_paths.csv",
        behavior_path,
        output_dir / "test416_controller_behavior_summary.json",
    ]
    source_paths = [
        Path("docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md"),
        Path("src/run_supplementary_retrieval.py"),
        Path("src/bootstrap_supplementary.py"),
        Path("src/analyze_controller_behavior.py"),
        Path("src/audit_supplementary.py"),
        Path("src/run_controller_v3.py"),
    ]
    artifacts = [input_path, *primary_paths, *summary_paths, *source_paths]
    artifacts.extend(Path(result["path"]) for result in methods.values())

    manifest_rows: list[dict[str, Any]] = []
    for path in artifacts:
        if not path.exists():
            errors.append(f"Missing required artifact: {path}")
            continue
        manifest_rows.append(
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )

    audit = {
        "status": "pass" if not errors else "fail",
        "run_name": args.run_name,
        "input": str(input_path),
        "input_sha256": sha256(input_path),
        "papers": paper_count,
        "questions": len(expected_keys),
        "methods": methods,
        "budget_matching": {
            "rows": len(budget_rows),
            "count_max_abs_unit_difference": max(count_differences, default=0),
            "token_exact_word_matches": sum(value == 0 for value in token_differences),
            "token_mean_abs_word_difference": (
                sum(token_differences) / len(token_differences)
                if token_differences
                else 0.0
            ),
            "token_max_abs_word_difference": max(token_differences, default=0),
        },
        "controller_behavior": {
            "paired_rows": len(behavior_rows),
            "decision_path_rows": len(path_rows),
            "decision_path_question_total": path_total,
        },
        "bootstrap": bootstrap,
        "errors": errors,
    }

    audit_path = output_dir / "test416_supplementary_integrity_audit.json"
    manifest_path = output_dir / "test416_supplementary_sha256_manifest.csv"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Audit status: {audit['status']}")
    print(f"Papers: {paper_count}; questions: {len(expected_keys)}")
    print(f"Methods checked: {len(methods)}")
    print(f"Saved audit to {audit_path}")
    print(f"Saved SHA-256 manifest to {manifest_path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
