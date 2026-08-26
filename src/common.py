import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def write_jsonl(records: Iterable[Dict[str, Any]], path: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError("No rows to write.")

    fieldnames = list(rows[0].keys())

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", str(text).lower())


def estimate_tokens_from_words(words: float) -> int:
    """A simple cost proxy for English scientific text."""
    return int(round(words * 1.3))


def extract_reference_answers(raw_answers: Any) -> List[str]:
    if not isinstance(raw_answers, dict):
        return []

    reference_answers: List[str] = []

    for answer in raw_answers.get("answer", []):
        if not isinstance(answer, dict):
            continue

        if answer.get("unanswerable", False):
            reference_answers.append("unanswerable")
            continue

        free_form = answer.get("free_form_answer", "")
        if free_form:
            reference_answers.append(free_form)

        extractive_spans = answer.get("extractive_spans", [])
        if extractive_spans:
            reference_answers.extend(extractive_spans)

        yes_no = answer.get("yes_no", None)
        if yes_no is not None:
            reference_answers.append(str(yes_no))

    return reference_answers


def extract_gold_evidence(raw_answers: Any) -> List[str]:
    if not isinstance(raw_answers, dict):
        return []

    evidence_texts: List[str] = []

    for answer in raw_answers.get("answer", []):
        if not isinstance(answer, dict):
            continue

        evidence = answer.get("evidence", [])
        if evidence:
            evidence_texts.extend(evidence)

    seen = set()
    unique_evidence: List[str] = []

    for evidence in evidence_texts:
        normalized = " ".join(str(evidence).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_evidence.append(normalized)

    return unique_evidence


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0
