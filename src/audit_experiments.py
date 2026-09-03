"""Audit the saved Validation50 experiment artifacts and export a machine-readable archive.

This script does not rerun retrieval or answer generation. It reads the saved
artifacts, recomputes descriptive statistics, and writes:

* docs/experiment_audit.json
* docs/file_manifest_sha256.csv

Run it from the project root with::

    .\\.venv\\Scripts\\python.exe src\\audit_experiments.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from common import extract_gold_evidence, extract_reference_answers, read_jsonl
from evaluate_generated_answers import latest_records, score_answer
from retrieval import compute_cost_stats, evaluate_predictions


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
AUDIT_PATH = DOCS_DIR / "experiment_audit.json"
MANIFEST_PATH = DOCS_DIR / "file_manifest_sha256.csv"
OVERVIEW_PATH = DOCS_DIR / "experiment_results_overview.csv"

RETRIEVAL_FILES = {
    "BM25_top1": "outputs/validation50_bm25_top1.jsonl",
    "BM25_top3": "outputs/validation50_bm25_top3.jsonl",
    "BM25_top5": "outputs/validation50_bm25_top5.jsonl",
    "BM25_top10": "outputs/validation50_bm25_top10.jsonl",
    "BM25_top20": "outputs/validation50_bm25_top20.jsonl",
    "ControllerV3": "outputs/validation50_controller_v3.jsonl",
    "ControllerV3_no_section": "outputs/validation50_controller_v3_no_section.jsonl",
}

EXPERIMENT_FILES = [
    "data/processed/qasper_train_100.jsonl",
    "data/processed/qasper_validation_50.jsonl",
    *RETRIEVAL_FILES.values(),
    "outputs/validation50_method_comparison_threshold05.csv",
    "outputs/error_analysis_controller_v3_validation50.csv",
    "outputs/generation_prompts_validation50.jsonl",
    "outputs/ollama_generations_validation50.jsonl",
    "outputs/ollama_answer_scores_validation50.csv",
    "outputs/ollama_answer_summary_validation50.csv",
]


def round_or_zero(value: float, digits: int = 6) -> float:
    return round(value, digits) if value else 0.0


def safe_mean(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.mean(values) if values else 0.0


def safe_median(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.median(values) if values else 0.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_rows(relative_path: str) -> List[Dict[str, str]]:
    with (ROOT / relative_path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def summarize_dataset(relative_path: str) -> Dict[str, Any]:
    papers = read_jsonl(str(ROOT / relative_path))
    unit_types: Counter[str] = Counter()
    section_names: Counter[str] = Counter()
    answer_forms: Counter[str] = Counter()
    unit_words: List[int] = []
    total_questions = 0
    questions_with_gold = 0
    total_gold_spans = 0
    total_reference_answers = 0

    for paper in papers:
        for unit in paper.get("evidence_units", []):
            unit_types[unit.get("unit_type", "")] += 1
            section_name = " ".join(str(unit.get("section_name", "")).split()).casefold()
            section_names[section_name] += 1
            unit_words.append(int(unit.get("word_count", 0)))

        for question in paper.get("questions", []):
            total_questions += 1
            raw_answers = question.get("raw_answers", {})
            gold = extract_gold_evidence(raw_answers)
            refs = extract_reference_answers(raw_answers)
            total_gold_spans += len(gold)
            total_reference_answers += len(refs)
            if gold:
                questions_with_gold += 1

            for answer in raw_answers.get("answer", []) if isinstance(raw_answers, dict) else []:
                if answer.get("unanswerable", False):
                    answer_forms["unanswerable_annotations"] += 1
                if answer.get("free_form_answer", ""):
                    answer_forms["free_form_annotations"] += 1
                if answer.get("extractive_spans", []):
                    answer_forms["extractive_annotations"] += 1
                if answer.get("yes_no", None) is not None:
                    answer_forms["yes_no_annotations"] += 1

    return {
        "path": relative_path,
        "papers": len(papers),
        "questions": total_questions,
        "questions_with_gold_evidence": questions_with_gold,
        "total_gold_evidence_spans": total_gold_spans,
        "total_reference_answer_strings": total_reference_answers,
        "evidence_units": sum(unit_types.values()),
        "unit_type_counts": dict(unit_types),
        "top_section_names": dict(section_names.most_common(20)),
        "answer_annotation_forms_nonexclusive": dict(answer_forms),
        "avg_unit_words": round_or_zero(safe_mean(unit_words), 2),
        "median_unit_words": round_or_zero(safe_median(unit_words), 2),
        "min_unit_words": min(unit_words) if unit_words else 0,
        "max_unit_words": max(unit_words) if unit_words else 0,
    }


def summarize_retrieval() -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for method, relative_path in RETRIEVAL_FILES.items():
        records = read_jsonl(str(ROOT / relative_path))
        keys = [(row.get("paper_id", ""), row.get("question_id", "")) for row in records]
        evaluation = evaluate_predictions(records, threshold=0.5)
        cost = compute_cost_stats(records)
        summary = {
            "path": relative_path,
            "records": len(records),
            "unique_paper_question_keys": len(set(keys)),
            "duplicate_keys": len(keys) - len(set(keys)),
            **evaluation,
            **cost,
        }
        tokens = float(summary["avg_estimated_tokens"])
        summary["recall_per_1k_tokens"] = round_or_zero(
            round(float(summary["evidence_recall"]), 4) / tokens * 1000 if tokens else 0,
            4,
        )
        output[method] = summary

    stored_rows = csv_rows("outputs/validation50_method_comparison_threshold05.csv")
    stored_by_method = {row["method"]: row for row in stored_rows}
    checked_fields = {
        "question_hit_rate": 4,
        "evidence_recall": 4,
        "average_best_overlap": 4,
        "avg_retrieved_units": 2,
        "avg_evidence_words": 2,
        "avg_estimated_tokens": 0,
        "recall_per_1k_tokens": 4,
    }
    mismatches = []
    for method in RETRIEVAL_FILES:
        stored = stored_by_method.get(method)
        if stored is None:
            mismatches.append({"method": method, "issue": "missing summary row"})
            continue
        for field, digits in checked_fields.items():
            recomputed = round(float(output[method][field]), digits)
            saved = round(float(stored[field]), digits)
            if recomputed != saved:
                mismatches.append(
                    {
                        "method": method,
                        "field": field,
                        "recomputed": recomputed,
                        "saved": saved,
                    }
                )
    output["stored_summary_integrity"] = {
        "path": "outputs/validation50_method_comparison_threshold05.csv",
        "expected_rows": len(RETRIEVAL_FILES),
        "actual_rows": len(stored_rows),
        "checked_fields": list(checked_fields),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }

    controller = read_jsonl(str(ROOT / RETRIEVAL_FILES["ControllerV3"]))
    action_counts: Counter[str] = Counter()
    action_sequence_counts: Counter[str] = Counter()
    selected_by_counts: Counter[str] = Counter()
    question_type_counts: Counter[str] = Counter()

    for row in controller:
        sequence = []
        for action in row.get("actions", []):
            name = action.get("action", "")
            action_counts[name] += 1
            sequence.append(name)
        action_sequence_counts[" -> ".join(sequence)] += 1

        for unit in row.get("retrieved_units", []):
            selected_by_counts[unit.get("selected_by", "")] += 1

        for question_type, active in row.get("question_type", {}).items():
            if active:
                question_type_counts[question_type] += 1

    output["ControllerV3_diagnostics"] = {
        "question_type_counts_nonexclusive": dict(question_type_counts),
        "action_counts": dict(action_counts),
        "action_sequence_counts": dict(action_sequence_counts),
        "selected_unit_counts_by_action": dict(selected_by_counts),
    }
    return output


def summarize_errors() -> Dict[str, Any]:
    rows = csv_rows("outputs/error_analysis_controller_v3_validation50.csv")
    categories = Counter(row["category"] for row in rows)
    failures = {key: value for key, value in categories.items() if key != "success"}
    total = len(rows)
    failure_total = sum(failures.values())
    return {
        "path": "outputs/error_analysis_controller_v3_validation50.csv",
        "rows_questions_with_gold": total,
        "category_counts": dict(categories),
        "failure_category_counts": failures,
        "failure_category_share_of_all_gold_questions": {
            key: round_or_zero(value / total, 6) for key, value in failures.items()
        },
        "failure_category_share_within_failures": {
            key: round_or_zero(value / failure_total, 6) for key, value in failures.items()
        },
    }


def summarize_prompts() -> Dict[str, Any]:
    rows = read_jsonl(str(ROOT / "outputs/generation_prompts_validation50.jsonl"))
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row.get("method", "")].append(row)

    methods: Dict[str, Any] = {}
    for method, method_rows in sorted(groups.items()):
        prompt_chars = [len(row.get("prompt", "")) for row in method_rows]
        keys = [(row.get("method", ""), row.get("question_id", "")) for row in method_rows]
        methods[method] = {
            "records": len(method_rows),
            "unique_method_question_keys": len(set(keys)),
            "duplicate_keys": len(keys) - len(set(keys)),
            "avg_num_retrieved_units_before_char_cap": round_or_zero(
                safe_mean(float(row.get("num_retrieved_units", 0)) for row in method_rows), 2
            ),
            "avg_prompt_chars": round_or_zero(safe_mean(prompt_chars), 2),
            "median_prompt_chars": round_or_zero(safe_median(prompt_chars), 2),
            "min_prompt_chars": min(prompt_chars) if prompt_chars else 0,
            "max_prompt_chars": max(prompt_chars) if prompt_chars else 0,
        }

    rows_by_key = {
        (row.get("method", ""), row.get("question_id", "")): row for row in rows
    }
    qids = {row.get("question_id", "") for row in rows}
    pair_comparisons: Dict[str, Any] = {}
    pairs = [
        ("BM25_top10", "BM25_top20"),
        ("BM25_top5", "BM25_top10"),
        ("ControllerV3", "BM25_top5"),
        ("ControllerV3", "BM25_top10"),
        ("ControllerV3", "BM25_top20"),
    ]
    for left, right in pairs:
        equal = 0
        compared = 0
        for qid in qids:
            left_row = rows_by_key.get((left, qid))
            right_row = rows_by_key.get((right, qid))
            if left_row is None or right_row is None:
                continue
            compared += 1
            equal += left_row.get("prompt", "") == right_row.get("prompt", "")
        pair_comparisons[f"{left}_vs_{right}"] = {
            "paired_questions": compared,
            "identical_prompt_count": equal,
            "different_prompt_count": compared - equal,
        }

    return {
        "path": "outputs/generation_prompts_validation50.jsonl",
        "total_records": len(rows),
        "methods": methods,
        "evidence_character_cap": 6000,
        "paired_prompt_comparisons": pair_comparisons,
    }


def summarize_generation() -> Dict[str, Any]:
    relative_path = "outputs/ollama_generations_validation50.jsonl"
    raw_records = read_jsonl(str(ROOT / relative_path))
    records = latest_records(raw_records)
    raw_keys = [(row.get("method", ""), row.get("question_id", "")) for row in raw_records]
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[row.get("method", "")].append(row)

    method_runs: Dict[str, Any] = {}
    for method, method_rows in sorted(grouped.items()):
        ok_rows = [row for row in method_rows if row.get("status") == "ok"]
        timestamps = [row.get("created_at", "") for row in method_rows if row.get("created_at")]
        method_runs[method] = {
            "latest_unique_records": len(method_rows),
            "successful_records": len(ok_rows),
            "error_records": len(method_rows) - len(ok_rows),
            "success_rate": round_or_zero(len(ok_rows) / len(method_rows) if method_rows else 0),
            "models": dict(Counter(row.get("model", "") for row in method_rows)),
            "done_reasons": dict(Counter(row.get("done_reason", "") for row in method_rows)),
            "avg_prompt_tokens": round_or_zero(
                safe_mean(float(row.get("prompt_eval_count", 0)) for row in ok_rows), 2
            ),
            "avg_output_tokens": round_or_zero(
                safe_mean(float(row.get("eval_count", 0)) for row in ok_rows), 2
            ),
            "total_prompt_tokens": int(sum(float(row.get("prompt_eval_count", 0)) for row in ok_rows)),
            "total_output_tokens": int(sum(float(row.get("eval_count", 0)) for row in ok_rows)),
            "avg_wall_time_seconds_diagnostic_only": round_or_zero(
                safe_mean(float(row.get("wall_time_seconds", 0)) for row in ok_rows), 3
            ),
            "first_created_at_utc": min(timestamps) if timestamps else "",
            "last_created_at_utc": max(timestamps) if timestamps else "",
        }

    score_rows = csv_rows("outputs/ollama_answer_scores_validation50.csv")
    saved_scores_by_key = {
        (row["method"], row["question_id"]): row for row in score_rows
    }
    recomputed_score_mismatches = []
    raw_latest_keys = {
        (row.get("method", ""), row.get("question_id", "")) for row in records
    }
    saved_score_keys = set(saved_scores_by_key)
    for record in records:
        key = (record.get("method", ""), record.get("question_id", ""))
        saved = saved_scores_by_key.get(key)
        if saved is None:
            continue
        f1, exact_match = score_answer(
            record.get("generated_answer", ""),
            record.get("reference_answers", []),
        )
        if round(f1, 6) != float(saved["answer_f1"]) or round(
            exact_match, 6
        ) != float(saved["exact_match"]):
            recomputed_score_mismatches.append(
                {
                    "method": key[0],
                    "question_id": key[1],
                    "recomputed_f1": round(f1, 6),
                    "saved_f1": float(saved["answer_f1"]),
                    "recomputed_exact_match": round(exact_match, 6),
                    "saved_exact_match": float(saved["exact_match"]),
                }
            )
    score_groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in score_rows:
        score_groups[row["method"]].append(row)

    score_summary: Dict[str, Any] = {}
    scores_by_key: Dict[tuple[str, str], float] = {}
    for method, rows in sorted(score_groups.items()):
        f1_values = [float(row["answer_f1"]) for row in rows if row["status"] == "ok"]
        em_values = [float(row["exact_match"]) for row in rows if row["status"] == "ok"]
        for row in rows:
            scores_by_key[(method, row["question_id"])] = float(row["answer_f1"])
        score_summary[method] = {
            "records": len(rows),
            "answer_f1_mean": round_or_zero(safe_mean(f1_values), 6),
            "answer_f1_median": round_or_zero(safe_median(f1_values), 6),
            "exact_match_mean": round_or_zero(safe_mean(em_values), 6),
            "zero_f1_count": sum(value == 0 for value in f1_values),
            "positive_f1_count": sum(value > 0 for value in f1_values),
            "f1_at_least_0_5_count": sum(value >= 0.5 for value in f1_values),
            "exact_match_count": int(sum(em_values)),
        }

    paired: Dict[str, Any] = {}
    controller_method = "ControllerV3"
    controller_qids = {
        qid for method, qid in scores_by_key if method == controller_method
    }
    for baseline in ["BM25_top5", "BM25_top10", "BM25_top20"]:
        differences = []
        wins = ties = losses = 0
        for qid in sorted(controller_qids):
            controller_score = scores_by_key[(controller_method, qid)]
            baseline_score = scores_by_key[(baseline, qid)]
            difference = controller_score - baseline_score
            differences.append(difference)
            if difference > 1e-12:
                wins += 1
            elif difference < -1e-12:
                losses += 1
            else:
                ties += 1
        paired[f"ControllerV3_vs_{baseline}"] = {
            "paired_questions": len(differences),
            "controller_wins": wins,
            "ties": ties,
            "controller_losses": losses,
            "mean_f1_difference_controller_minus_baseline": round_or_zero(
                safe_mean(differences), 6
            ),
        }

    answers_by_key = {
        (row.get("method", ""), row.get("question_id", "")): row.get(
            "generated_answer", ""
        )
        for row in records
    }
    answer_equality: Dict[str, Any] = {}
    answer_pairs = [
        ("BM25_top10", "BM25_top20"),
        ("BM25_top5", "BM25_top10"),
        ("ControllerV3", "BM25_top5"),
        ("ControllerV3", "BM25_top10"),
        ("ControllerV3", "BM25_top20"),
    ]
    for left, right in answer_pairs:
        common_qids = sorted(
            {qid for method, qid in answers_by_key if method == left}
            & {qid for method, qid in answers_by_key if method == right}
        )
        equal = sum(
            answers_by_key[(left, qid)] == answers_by_key[(right, qid)]
            for qid in common_qids
        )
        answer_equality[f"{left}_vs_{right}"] = {
            "paired_questions": len(common_qids),
            "identical_generated_answer_count": equal,
            "different_generated_answer_count": len(common_qids) - equal,
        }

    return {
        "path": relative_path,
        "raw_line_records": len(raw_records),
        "latest_unique_method_question_records": len(records),
        "duplicate_or_superseded_raw_records": len(raw_records) - len(set(raw_keys)),
        "method_runs": method_runs,
        "answer_score_distributions": score_summary,
        "saved_answer_score_integrity": {
            "path": "outputs/ollama_answer_scores_validation50.csv",
            "raw_latest_keys": len(raw_latest_keys),
            "saved_score_keys": len(saved_score_keys),
            "missing_saved_score_keys": len(raw_latest_keys - saved_score_keys),
            "extra_saved_score_keys": len(saved_score_keys - raw_latest_keys),
            "recomputed_score_mismatch_count": len(recomputed_score_mismatches),
            "recomputed_score_mismatches": recomputed_score_mismatches,
        },
        "paired_f1_comparisons": paired,
        "paired_generated_answer_comparisons": answer_equality,
        "wall_time_warning": (
            "Generation was completed through interrupted/resumed sessions. "
            "Wall-clock fields are diagnostics, not a controlled benchmark."
        ),
    }


def inspect_file(relative_path: str) -> Dict[str, Any]:
    path = ROOT / relative_path
    result: Dict[str, Any] = {
        "path": relative_path,
        "exists": path.exists(),
    }
    if not path.exists():
        return result

    result["size_bytes"] = path.stat().st_size
    result["sha256"] = sha256_file(path)
    if path.suffix == ".jsonl":
        rows = read_jsonl(str(path))
        result["records"] = len(rows)
        result["fields"] = list(rows[0].keys()) if rows else []
    elif path.suffix == ".csv":
        rows = csv_rows(relative_path)
        result["records"] = len(rows)
        result["fields"] = list(rows[0].keys()) if rows else []
    return result


def manifest_candidates() -> List[Path]:
    candidates = [ROOT / "README.md", ROOT / "requirements.txt"]
    for directory in [ROOT / "src", ROOT / "data" / "processed", ROOT / "outputs", DOCS_DIR]:
        if directory.exists():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())

    excluded = {MANIFEST_PATH.resolve()}
    return sorted(
        {
            path.resolve()
            for path in candidates
            if path.resolve() not in excluded
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        },
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def write_manifest() -> None:
    with MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["relative_path", "size_bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        for path in manifest_candidates():
            writer.writerow(
                {
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )


def write_overview(audit: Dict[str, Any]) -> None:
    answer_summaries = audit["answer_generation"]["answer_score_distributions"]
    generation_runs = audit["answer_generation"]["method_runs"]
    fields = [
        "method",
        "experiment_role",
        "records",
        "evidence_recall_at_0_5",
        "question_hit_rate_at_0_5",
        "average_best_overlap",
        "avg_retrieved_units",
        "avg_evidence_words",
        "avg_estimated_retrieval_tokens",
        "recall_per_1k_tokens",
        "answer_f1",
        "exact_match",
        "generation_success_rate",
        "avg_actual_prompt_tokens",
        "avg_output_tokens",
        "notes",
    ]
    with OVERVIEW_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for method in RETRIEVAL_FILES:
            stats = audit["retrieval"][method]
            answers = answer_summaries.get(method, {})
            run = generation_runs.get(method, {})
            if method.startswith("BM25"):
                role = "fixed_top_k_baseline"
            elif method == "ControllerV3_no_section":
                role = "section_expansion_ablation"
            else:
                role = "proposed_method"
            notes = ""
            if method in {"BM25_top10", "BM25_top20"}:
                notes = "Generation prompt is affected by the 6000-character evidence cap."
            writer.writerow(
                {
                    "method": method,
                    "experiment_role": role,
                    "records": stats["records"],
                    "evidence_recall_at_0_5": round(stats["evidence_recall"], 4),
                    "question_hit_rate_at_0_5": round(stats["question_hit_rate"], 4),
                    "average_best_overlap": round(stats["average_best_overlap"], 4),
                    "avg_retrieved_units": stats["avg_retrieved_units"],
                    "avg_evidence_words": stats["avg_evidence_words"],
                    "avg_estimated_retrieval_tokens": stats["avg_estimated_tokens"],
                    "recall_per_1k_tokens": stats["recall_per_1k_tokens"],
                    "answer_f1": answers.get("answer_f1_mean", ""),
                    "exact_match": answers.get("exact_match_mean", ""),
                    "generation_success_rate": run.get("success_rate", ""),
                    "avg_actual_prompt_tokens": run.get("avg_prompt_tokens", ""),
                    "avg_output_tokens": run.get("avg_output_tokens", ""),
                    "notes": notes,
                }
            )


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    audit = {
        "archive_schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root_name": "cost-aware-evidence-controller",
        "experiment_completion": {
            "retrieval_methods_expected": list(RETRIEVAL_FILES),
            "generation_methods_expected": [
                "BM25_top5",
                "BM25_top10",
                "BM25_top20",
                "ControllerV3",
            ],
            "expected_questions_per_generation_method": 156,
            "expected_total_generation_records": 624,
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_processors_visible": os.cpu_count(),
        },
        "datasets": {
            "train_100": summarize_dataset("data/processed/qasper_train_100.jsonl"),
            "validation_50": summarize_dataset("data/processed/qasper_validation_50.jsonl"),
        },
        "retrieval": summarize_retrieval(),
        "error_analysis": summarize_errors(),
        "generation_prompts": summarize_prompts(),
        "answer_generation": summarize_generation(),
        "artifact_inventory": [inspect_file(path) for path in EXPERIMENT_FILES],
    }

    with AUDIT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    write_overview(audit)
    write_manifest()

    generation = audit["answer_generation"]
    print(f"Saved audit: {AUDIT_PATH.relative_to(ROOT)}")
    print(f"Saved manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Saved overview: {OVERVIEW_PATH.relative_to(ROOT)}")
    print(
        "Generation records: "
        f"{generation['latest_unique_method_question_records']} unique latest records"
    )
    for method, stats in generation["method_runs"].items():
        print(
            f"  {method}: {stats['successful_records']}/"
            f"{stats['latest_unique_records']} successful"
        )


if __name__ == "__main__":
    main()
