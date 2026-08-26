from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from common import read_jsonl, write_csv, write_jsonl
from retrieval import (
    compute_cost_stats,
    evaluate_predictions,
    get_retrievable_units,
    rank_units,
)
from run_retrieval_experiment import make_summary_row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run frozen supplementary QASPER retrieval controls."
    )
    parser.add_argument("--input", default="data/processed/qasper_test_416.jsonl")
    parser.add_argument(
        "--controller", default="outputs/test416/test416_controller_v3.jsonl"
    )
    parser.add_argument(
        "--no-section",
        default="outputs/test416/test416_controller_v3_no_section.jsonl",
    )
    parser.add_argument("--output-dir", default="outputs/supplementary")
    parser.add_argument("--run-name", default="test416_supplementary")
    parser.add_argument("--threshold", type=float, default=0.5)
    return parser.parse_args()


def keyed(records: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    output: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for record in records:
        key = (str(record["paper_id"]), str(record["question_id"]))
        if key in output:
            raise ValueError(f"Duplicate paper/question key: {key}")
        output[key] = record
    return output


def prediction_unit(
    unit: Dict[str, Any], rank: int, selected_by: str
) -> Dict[str, Any]:
    return {
        "rank": rank,
        "score": 0.0,
        "unit_id": unit["unit_id"],
        "unit_type": unit["unit_type"],
        "section_name": unit["section_name"],
        "text": unit["text"],
        "word_count": unit.get("word_count", len(unit.get("text", "").split())),
        "selected_by": selected_by,
    }


def reference_prediction(
    paper: Dict[str, Any],
    question: Dict[str, Any],
    frozen_record: Dict[str, Any],
    selected: List[Dict[str, Any]],
    action: str,
) -> Dict[str, Any]:
    return {
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "question_id": question["question_id"],
        "question": question["question"],
        "reference_answers": frozen_record.get("reference_answers", []),
        "gold_evidence": frozen_record.get("gold_evidence", []),
        "retrieved_units": selected,
        "actions": [
            {
                "action": action,
                "added_units": len(selected),
                "reason": "Frozen supplementary reference strategy.",
            }
        ],
    }


def clone_units(units: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [dict(unit) for unit in units]


def word_count(units: Iterable[Dict[str, Any]]) -> int:
    return sum(
        int(unit.get("word_count", len(unit.get("text", "").split())))
        for unit in units
    )


def add_generic_count_matched(
    no_section_units: List[Dict[str, Any]],
    ranked_units: List[Dict[str, Any]],
    target_count: int,
) -> List[Dict[str, Any]]:
    selected = clone_units(no_section_units[:target_count])
    seen = {unit["unit_id"] for unit in selected}
    for unit in ranked_units:
        if len(selected) >= target_count:
            break
        if unit["unit_id"] in seen:
            continue
        added = dict(unit)
        added["selected_by"] = "GenericCountMatchedExpansion"
        selected.append(added)
        seen.add(unit["unit_id"])
    return selected


def add_generic_token_matched(
    no_section_units: List[Dict[str, Any]],
    ranked_units: List[Dict[str, Any]],
    target_words: int,
) -> List[Dict[str, Any]]:
    selected = clone_units(no_section_units)
    current_words = word_count(selected)

    while selected:
        last_words = int(
            selected[-1].get(
                "word_count", len(selected[-1].get("text", "").split())
            )
        )
        if abs(target_words - (current_words - last_words)) >= abs(
            target_words - current_words
        ):
            break
        selected.pop()
        current_words -= last_words

    seen = {unit["unit_id"] for unit in selected}

    for unit in ranked_units:
        if unit["unit_id"] in seen:
            continue
        unit_words = int(unit.get("word_count", len(unit.get("text", "").split())))
        before = abs(target_words - current_words)
        after = abs(target_words - (current_words + unit_words))
        if after >= before:
            break
        added = dict(unit)
        added["selected_by"] = "GenericTokenMatchedExpansion"
        selected.append(added)
        seen.add(unit["unit_id"])
        current_words += unit_words
    return selected


def generic_prediction(
    frozen_full: Dict[str, Any],
    frozen_no_section: Dict[str, Any],
    selected: List[Dict[str, Any]],
    action: str,
) -> Dict[str, Any]:
    record = {
        field: frozen_full.get(field)
        for field in (
            "paper_id",
            "title",
            "question_id",
            "question",
            "question_type",
            "reference_answers",
            "gold_evidence",
        )
    }
    added = len(selected) - len(frozen_no_section.get("retrieved_units", []))
    record["retrieved_units"] = selected
    record["actions"] = clone_units(frozen_no_section.get("actions", [])) + [
        {
            "action": action,
            "added_units": added,
            "reason": "Gold-independent generic BM25 budget-matching control.",
        }
    ]
    return record


def summarize(
    method: str,
    predictions: List[Dict[str, Any]],
    threshold: float,
) -> Dict[str, Any]:
    return make_summary_row(
        method=method,
        eval_stats=evaluate_predictions(predictions, threshold=threshold),
        cost_stats=compute_cost_stats(predictions),
        threshold=threshold,
    )


def main() -> None:
    args = parse_args()
    papers = read_jsonl(args.input)
    full_by_key = keyed(read_jsonl(args.controller))
    no_section_by_key = keyed(read_jsonl(args.no_section))
    if set(full_by_key) != set(no_section_by_key):
        raise ValueError("Frozen controller and no-section keys do not align.")

    abstract_only: List[Dict[str, Any]] = []
    read_all: List[Dict[str, Any]] = []
    generic_count: List[Dict[str, Any]] = []
    generic_token: List[Dict[str, Any]] = []
    match_rows: List[Dict[str, Any]] = []

    for paper in papers:
        retrievable = get_retrievable_units(paper["evidence_units"])
        abstract_units = [
            unit for unit in retrievable if unit.get("unit_type") == "abstract"
        ]
        for question in paper["questions"]:
            key = (str(paper["paper_id"]), str(question["question_id"]))
            frozen_full = full_by_key[key]
            frozen_no_section = no_section_by_key[key]

            abstract_selected = [
                prediction_unit(unit, index, "AbstractOnly")
                for index, unit in enumerate(abstract_units, start=1)
            ]
            all_selected = [
                prediction_unit(unit, index, "ReadAll")
                for index, unit in enumerate(retrievable, start=1)
            ]
            abstract_only.append(
                reference_prediction(
                    paper,
                    question,
                    frozen_full,
                    abstract_selected,
                    "AbstractOnly",
                )
            )
            read_all.append(
                reference_prediction(
                    paper, question, frozen_full, all_selected, "ReadAll"
                )
            )

            ranked = rank_units(
                question=question["question"],
                units=retrievable,
                top_k=len(retrievable),
            )
            full_units = frozen_full.get("retrieved_units", [])
            no_section_units = frozen_no_section.get("retrieved_units", [])
            count_selected = add_generic_count_matched(
                no_section_units, ranked, len(full_units)
            )
            token_selected = add_generic_token_matched(
                no_section_units, ranked, word_count(full_units)
            )
            generic_count.append(
                generic_prediction(
                    frozen_full,
                    frozen_no_section,
                    count_selected,
                    "GenericCountMatchedExpansion",
                )
            )
            generic_token.append(
                generic_prediction(
                    frozen_full,
                    frozen_no_section,
                    token_selected,
                    "GenericTokenMatchedExpansion",
                )
            )
            full_words = word_count(full_units)
            match_rows.append(
                {
                    "paper_id": key[0],
                    "question_id": key[1],
                    "full_units": len(full_units),
                    "count_matched_units": len(count_selected),
                    "token_matched_units": len(token_selected),
                    "full_words": full_words,
                    "count_matched_words": word_count(count_selected),
                    "token_matched_words": word_count(token_selected),
                    "count_unit_difference": len(count_selected) - len(full_units),
                    "count_word_difference": word_count(count_selected) - full_words,
                    "token_unit_difference": len(token_selected) - len(full_units),
                    "token_word_difference": word_count(token_selected) - full_words,
                }
            )

    expected_keys = set(full_by_key)
    methods = {
        "AbstractOnly": abstract_only,
        "ReadAll": read_all,
        "GenericCountMatched": generic_count,
        "GenericTokenMatched": generic_token,
    }
    for method, records in methods.items():
        if set(keyed(records)) != expected_keys:
            raise ValueError(f"Question alignment differs for {method}.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / args.run_name
    file_suffixes = {
        "AbstractOnly": "abstract_only",
        "ReadAll": "read_all",
        "GenericCountMatched": "generic_count_matched",
        "GenericTokenMatched": "generic_token_matched",
    }
    summary_rows = []
    for method, records in methods.items():
        write_jsonl(records, f"{prefix}_{file_suffixes[method]}.jsonl")
        summary_rows.append(summarize(method, records, args.threshold))

    write_csv(summary_rows, f"{prefix}_retrieval_summary.csv")
    write_csv(match_rows, f"{prefix}_budget_match_details.csv")

    audit = {
        "run_name": args.run_name,
        "threshold": args.threshold,
        "papers": len({key[0] for key in expected_keys}),
        "questions": len(expected_keys),
        "methods": {
            method: {
                "records": len(records),
                "unique_keys": len(keyed(records)),
            }
            for method, records in methods.items()
        },
        "count_match": {
            "exact_unit_matches": sum(
                row["count_unit_difference"] == 0 for row in match_rows
            ),
            "max_abs_unit_difference": max(
                abs(row["count_unit_difference"]) for row in match_rows
            ),
            "mean_word_difference": sum(
                row["count_word_difference"] for row in match_rows
            )
            / len(match_rows),
        },
        "token_match": {
            "exact_word_matches": sum(
                row["token_word_difference"] == 0 for row in match_rows
            ),
            "mean_abs_word_difference": sum(
                abs(row["token_word_difference"]) for row in match_rows
            )
            / len(match_rows),
            "max_abs_word_difference": max(
                abs(row["token_word_difference"]) for row in match_rows
            ),
        },
    }
    Path(f"{prefix}_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )

    print("Supplementary retrieval summary")
    for row in summary_rows:
        print(
            f"{row['method']:22s} recall={row['evidence_recall']:.4f} "
            f"hit={row['question_hit_rate']:.4f} "
            f"tokens={row['avg_estimated_tokens']}"
        )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
