from __future__ import annotations

import argparse
import json
import re
import string
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from common import read_jsonl, write_csv


COMPARISONS = [
    ("ControllerV3", "BM25_top7"),
    ("ControllerV3", "BM25_top8"),
    ("ControllerV3", "ControllerV3_no_section"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Official-style QASPER answer scoring and paper bootstrap."
    )
    parser.add_argument(
        "--prompts",
        default="outputs/supplementary/generation/test_generation_prompts.jsonl",
    )
    parser.add_argument(
        "--generations",
        default="outputs/supplementary/generation/test_generation_unique_generations.jsonl",
    )
    parser.add_argument("--output-dir", default="outputs/supplementary/generation")
    parser.add_argument("--prefix", default="test_generation")
    parser.add_argument("--limit-questions", type=int)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def normalize_answer(value: Any) -> str:
    text = str(value or "").lower()
    text = "".join(character for character in text if character not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def token_f1(prediction: str, reference: str) -> float:
    predicted = normalize_answer(prediction).split()
    gold = normalize_answer(reference).split()
    if not predicted or not gold:
        return float(predicted == gold)
    common = Counter(predicted) & Counter(gold)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(predicted)
    recall = overlap / len(gold)
    return 2 * precision * recall / (precision + recall)


def score_answer(
    prediction: str, references: list[dict[str, str]]
) -> tuple[float, float, str, str]:
    if not references:
        return 0.0, 0.0, "missing_reference", ""
    scored = [
        (
            token_f1(prediction, str(reference["answer"])),
            float(
                normalize_answer(prediction)
                == normalize_answer(str(reference["answer"]))
            ),
            str(reference["type"]),
            str(reference["answer"]),
        )
        for reference in references
    ]
    return max(scored, key=lambda item: item[0])


def select_prompt_records(
    records: list[dict[str, Any]], limit_questions: int | None
) -> list[dict[str, Any]]:
    if limit_questions is None:
        return records
    ordered_keys: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (str(record["paper_id"]), str(record["question_id"]))
        if key not in seen:
            seen.add(key)
            ordered_keys.append(key)
    selected = set(ordered_keys[:limit_questions])
    return [
        record
        for record in records
        if (str(record["paper_id"]), str(record["question_id"])) in selected
    ]


def latest_generations(path: str) -> dict[str, dict[str, Any]]:
    return {
        str(record["prompt_sha256"]): record for record in read_jsonl(path)
    }


def detail_rows(
    prompts: list[dict[str, Any]], generations: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for prompt in prompts:
        prompt_hash = str(prompt["prompt_sha256"])
        generation = generations.get(prompt_hash, {})
        status = str(generation.get("status", "missing"))
        prediction = str(generation.get("generated_answer", ""))
        references = prompt.get("reference_answers", [])
        f1, exact_match, best_type, best_reference = score_answer(
            prediction, references
        )
        reference_types = {str(reference["type"]) for reference in references}
        unanimously_unanswerable = reference_types == {"none"}
        rows.append(
            {
                "method": prompt["method"],
                "paper_id": prompt["paper_id"],
                "question_id": prompt["question_id"],
                "question": prompt["question"],
                "prompt_sha256": prompt_hash,
                "status": status,
                "generated_answer": prediction,
                "reference_answers": json.dumps(references, ensure_ascii=False),
                "best_reference": best_reference,
                "best_reference_type": best_type,
                "answer_f1": round(f1, 6),
                "exact_match": round(exact_match, 6),
                "unanimously_unanswerable": int(unanimously_unanswerable),
                "unanswerable_correct": int(
                    unanimously_unanswerable
                    and normalize_answer(prediction) == normalize_answer("Unanswerable")
                ),
                "source_retrieved_units": prompt["source_retrieved_units"],
                "retained_evidence_units": prompt["retained_evidence_units"],
                "retained_evidence_chars": prompt["retained_evidence_chars"],
                "prompt_tokens": int(generation.get("prompt_eval_count", 0)),
                "output_tokens": int(generation.get("eval_count", 0)),
                "wall_time_seconds": generation.get("wall_time_seconds", 0),
                "model": generation.get("model", ""),
                "error": generation.get("error", ""),
            }
        )
    return rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summaries(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[str(row["method"])].append(row)

    method_rows: list[dict[str, Any]] = []
    type_rows: list[dict[str, Any]] = []
    for method in sorted(by_method):
        items = by_method[method]
        successful = [item for item in items if item["status"] == "ok"]
        unanimous = [item for item in items if item["unanimously_unanswerable"]]
        method_rows.append(
            {
                "method": method,
                "records": len(items),
                "successful_records": len(successful),
                "success_rate": round(len(successful) / len(items), 6),
                "answer_f1": round(mean([float(item["answer_f1"]) for item in items]), 6),
                "exact_match": round(mean([float(item["exact_match"]) for item in items]), 6),
                "unanimously_unanswerable_questions": len(unanimous),
                "unanswerable_accuracy": round(
                    mean([float(item["unanswerable_correct"]) for item in unanimous]), 6
                ),
                "avg_prompt_tokens": round(mean([float(item["prompt_tokens"]) for item in items]), 2),
                "avg_output_tokens": round(mean([float(item["output_tokens"]) for item in items]), 2),
                "total_prompt_tokens_hypothetical": int(
                    sum(int(item["prompt_tokens"]) for item in items)
                ),
                "total_output_tokens_hypothetical": int(
                    sum(int(item["output_tokens"]) for item in items)
                ),
            }
        )
        for answer_type in ("extractive", "abstractive", "boolean", "none"):
            typed = [
                item for item in items if item["best_reference_type"] == answer_type
            ]
            type_rows.append(
                {
                    "method": method,
                    "best_reference_type": answer_type,
                    "questions": len(typed),
                    "answer_f1": round(
                        mean([float(item["answer_f1"]) for item in typed]), 6
                    ),
                    "exact_match": round(
                        mean([float(item["exact_match"]) for item in typed]), 6
                    ),
                }
            )
    return method_rows, type_rows


def paper_arrays(
    rows: list[dict[str, Any]], paper_ids: list[str]
) -> dict[str, np.ndarray]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["paper_id"])].append(row)
    return {
        "questions": np.array([len(grouped[paper_id]) for paper_id in paper_ids], dtype=float),
        "f1": np.array(
            [sum(float(item["answer_f1"]) for item in grouped[paper_id]) for paper_id in paper_ids]
        ),
        "em": np.array(
            [sum(float(item["exact_match"]) for item in grouped[paper_id]) for paper_id in paper_ids]
        ),
        "prompt_tokens": np.array(
            [sum(float(item["prompt_tokens"]) for item in grouped[paper_id]) for paper_id in paper_ids]
        ),
        "output_tokens": np.array(
            [sum(float(item["output_tokens"]) for item in grouped[paper_id]) for paper_id in paper_ids]
        ),
    }


def bootstrap(
    rows: list[dict[str, Any]], replicates: int, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[str(row["method"])].append(row)
    methods = sorted(by_method)
    reference_keys = {
        (str(row["paper_id"]), str(row["question_id"]))
        for row in by_method[methods[0]]
    }
    for method in methods:
        keys = {
            (str(row["paper_id"]), str(row["question_id"]))
            for row in by_method[method]
        }
        if keys != reference_keys or len(keys) != len(by_method[method]):
            raise ValueError(f"Question alignment or duplicates differ for {method}.")

    paper_ids = sorted({paper_id for paper_id, _ in reference_keys})
    arrays = {
        method: paper_arrays(by_method[method], paper_ids) for method in methods
    }
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(paper_ids), size=(replicates, len(paper_ids)))
    metrics: dict[str, dict[str, np.ndarray]] = {}
    point_metrics: dict[str, dict[str, float]] = {}
    for method in methods:
        selected_questions = arrays[method]["questions"][indices].sum(axis=1)
        metrics[method] = {
            metric: arrays[method][metric][indices].sum(axis=1) / selected_questions
            for metric in ("f1", "em", "prompt_tokens", "output_tokens")
        }
        total_questions = arrays[method]["questions"].sum()
        point_metrics[method] = {
            metric: float(arrays[method][metric].sum() / total_questions)
            for metric in ("f1", "em", "prompt_tokens", "output_tokens")
        }

    method_ci_rows: list[dict[str, Any]] = []
    for method in methods:
        for metric in ("f1", "em", "prompt_tokens", "output_tokens"):
            lower, upper = np.percentile(metrics[method][metric], [2.5, 97.5])
            method_ci_rows.append(
                {
                    "method": method,
                    "metric": metric,
                    "point_estimate": round(point_metrics[method][metric], 6),
                    "ci_lower": round(float(lower), 6),
                    "ci_upper": round(float(upper), 6),
                    "papers": len(paper_ids),
                    "replicates": replicates,
                    "seed": seed,
                    "resampling_unit": "paper",
                }
            )

    paired_rows: list[dict[str, Any]] = []
    for first, second in COMPARISONS:
        if first not in metrics or second not in metrics:
            continue
        for metric in ("f1", "em", "prompt_tokens", "output_tokens"):
            differences = metrics[first][metric] - metrics[second][metric]
            lower, upper = np.percentile(differences, [2.5, 97.5])
            paired_rows.append(
                {
                    "first_method": first,
                    "second_method": second,
                    "contrast": f"{first} - {second}",
                    "metric": metric,
                    "point_difference": round(
                        point_metrics[first][metric] - point_metrics[second][metric],
                        6,
                    ),
                    "ci_lower": round(float(lower), 6),
                    "ci_upper": round(float(upper), 6),
                    "papers": len(paper_ids),
                    "replicates": replicates,
                    "seed": seed,
                    "resampling_unit": "paper",
                }
            )
    return method_ci_rows, paired_rows


def main() -> None:
    args = parse_args()
    prompts = select_prompt_records(read_jsonl(args.prompts), args.limit_questions)
    generations = latest_generations(args.generations)
    rows = detail_rows(prompts, generations)
    method_rows, type_rows = summaries(rows)
    method_ci_rows, paired_rows = bootstrap(rows, args.replicates, args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, str(output_dir / f"{args.prefix}_answer_details.csv"))
    write_csv(method_rows, str(output_dir / f"{args.prefix}_answer_summary.csv"))
    write_csv(type_rows, str(output_dir / f"{args.prefix}_answer_by_type.csv"))
    write_csv(method_ci_rows, str(output_dir / f"{args.prefix}_answer_bootstrap_method_cis.csv"))
    write_csv(paired_rows, str(output_dir / f"{args.prefix}_answer_bootstrap_paired.csv"))

    selected_hashes = {str(prompt["prompt_sha256"]) for prompt in prompts}
    selected_generations = [
        generations[prompt_hash]
        for prompt_hash in selected_hashes
        if prompt_hash in generations and generations[prompt_hash].get("status") == "ok"
    ]
    audit = {
        "status": "pass"
        if all(row["status"] == "ok" for row in rows)
        and len(rows) == len(prompts)
        else "fail",
        "mode": "smoke" if args.limit_questions is not None else "frozen_sample",
        "methods": sorted({str(row["method"]) for row in rows}),
        "papers": len({str(row["paper_id"]) for row in rows}),
        "questions": len(
            {(str(row["paper_id"]), str(row["question_id"])) for row in rows}
        ),
        "method_question_records": len(rows),
        "unique_prompt_hashes": len(selected_hashes),
        "successful_unique_generations": len(selected_generations),
        "prompt_hash_reuse_verified": all(
            len(
                {
                    str(row["generated_answer"])
                    for row in rows
                    if row["prompt_sha256"] == prompt_hash
                }
            )
            == 1
            for prompt_hash in selected_hashes
        ),
        "actual_unique_prompt_tokens": sum(
            int(record.get("prompt_eval_count", 0)) for record in selected_generations
        ),
        "actual_unique_output_tokens": sum(
            int(record.get("eval_count", 0)) for record in selected_generations
        ),
        "bootstrap": {
            "replicates": args.replicates,
            "seed": args.seed,
            "resampling_unit": "paper",
            "ci_method": "paired percentile paper-cluster bootstrap",
        },
        "scoring": {
            "answer_f1": "official QASPER/SQuAD token F1; maximum over annotations",
            "answer_type": "type of first maximum-F1 reference, matching official evaluator tie behaviour",
            "exact_match": "supplementary normalized exact match",
            "unanswerable_accuracy": "exact Unanswerable match for unanimously unanswerable reference sets",
            "failed_or_missing_generations": "retained in denominator with zero F1/EM",
        },
    }
    audit_path = output_dir / f"{args.prefix}_answer_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print("Answer generation summary")
    for row in method_rows:
        print(
            f"{row['method']:25s} F1={row['answer_f1']:.4f} "
            f"EM={row['exact_match']:.4f} "
            f"tokens={row['avg_prompt_tokens']}+{row['avg_output_tokens']} "
            f"success={row['successful_records']}/{row['records']}"
        )
    print(f"Audit status: {audit['status']}; saved to {audit_path}")
    if audit["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
