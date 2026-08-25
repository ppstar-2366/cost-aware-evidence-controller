import argparse
import json
import re
import string
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from common import mean, read_jsonl, write_csv


DEFAULT_INPUT = "outputs/ollama_generations_validation50.jsonl"
DEFAULT_DETAILS = "outputs/ollama_answer_scores_validation50.csv"
DEFAULT_SUMMARY = "outputs/ollama_answer_summary_validation50.csv"


def latest_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest = {}
    for record in records:
        key = (record.get("method", ""), record.get("question_id", ""))
        latest[key] = record
    return list(latest.values())


def normalize_answer(text: Any) -> str:
    text = str(text or "").lower().strip()
    if text in {
        "not enough evidence",
        "not enough evidence.",
        "insufficient evidence",
        "unanswerable",
    }:
        return "unanswerable"

    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def token_f1(prediction: str, reference: str) -> float:
    pred_tokens = normalize_answer(prediction).split()
    ref_tokens = normalize_answer(reference).split()

    if not pred_tokens or not ref_tokens:
        return float(pred_tokens == ref_tokens)

    common = Counter(pred_tokens) & Counter(ref_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def score_answer(prediction: str, references: List[str]) -> Tuple[float, float]:
    if not references:
        return 0.0, 0.0

    f1 = max(token_f1(prediction, reference) for reference in references)
    exact_match = max(
        float(normalize_answer(prediction) == normalize_answer(reference))
        for reference in references
    )
    return f1, exact_match


def build_detail_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for record in records:
        prediction = record.get("generated_answer", "")
        references = record.get("reference_answers", [])
        f1, exact_match = score_answer(prediction, references)
        rows.append(
            {
                "method": record.get("method", ""),
                "paper_id": record.get("paper_id", ""),
                "question_id": record.get("question_id", ""),
                "question": record.get("question", ""),
                "status": record.get("status", ""),
                "generated_answer": prediction,
                "reference_answers": json.dumps(references, ensure_ascii=False),
                "answer_f1": round(f1, 6),
                "exact_match": round(exact_match, 6),
                "prompt_tokens": record.get("prompt_eval_count", 0),
                "output_tokens": record.get("eval_count", 0),
                "wall_time_seconds": record.get("wall_time_seconds", 0),
                "model": record.get("model", ""),
                "error": record.get("error", ""),
            }
        )
    return rows


def build_summary_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["method"]].append(row)

    summary = []
    for method in sorted(grouped):
        method_rows = grouped[method]
        successful = [row for row in method_rows if row["status"] == "ok"]
        summary.append(
            {
                "method": method,
                "model": successful[0]["model"] if successful else "",
                "total_records": len(method_rows),
                "successful_records": len(successful),
                "success_rate": round(len(successful) / len(method_rows), 6),
                "answer_f1": round(mean([float(row["answer_f1"]) for row in successful]), 6),
                "exact_match": round(mean([float(row["exact_match"]) for row in successful]), 6),
                "avg_prompt_tokens": round(mean([float(row["prompt_tokens"]) for row in successful]), 2),
                "avg_output_tokens": round(mean([float(row["output_tokens"]) for row in successful]), 2),
                "total_prompt_tokens": int(sum(float(row["prompt_tokens"]) for row in successful)),
                "total_output_tokens": int(sum(float(row["output_tokens"]) for row in successful)),
                "avg_wall_time_seconds": round(
                    mean([float(row["wall_time_seconds"]) for row in successful]), 3
                ),
            }
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate generated QASPER answers.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--details", default=DEFAULT_DETAILS)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = latest_records(read_jsonl(args.input))
    detail_rows = build_detail_rows(records)
    summary_rows = build_summary_rows(detail_rows)

    write_csv(detail_rows, args.details)
    write_csv(summary_rows, args.summary)

    print("Answer generation summary")
    print("=" * 90)
    for row in summary_rows:
        print(
            f"{row['method']:18s} | F1={row['answer_f1']:<8} | "
            f"EM={row['exact_match']:<8} | success={row['successful_records']}/{row['total_records']} | "
            f"tokens={row['avg_prompt_tokens']}+{row['avg_output_tokens']}"
        )
    print(f"Saved details to {args.details}")
    print(f"Saved summary to {args.summary}")


if __name__ == "__main__":
    main()
