from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from common import read_jsonl, write_jsonl


DEFAULT_METHOD_FILES = {
    "ControllerV3": "outputs/test416/test416_controller_v3.jsonl",
    "BM25_top7": "outputs/test416/test416_bm25_top7.jsonl",
    "BM25_top8": "outputs/test416/test416_bm25_top8.jsonl",
    "ControllerV3_no_section": "outputs/test416/test416_controller_v3_no_section.jsonl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze a paper-cluster sample and build deduplicated test prompts."
    )
    parser.add_argument("--input", default="data/processed/qasper_test_416.jsonl")
    parser.add_argument("--output-dir", default="outputs/supplementary/generation")
    parser.add_argument("--min-questions", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-evidence-chars", type=int, default=20000)
    parser.add_argument(
        "--method-file",
        action="append",
        default=[],
        help="Method mapping NAME=PATH; repeat for multiple methods.",
    )
    return parser.parse_args()


def parse_method_files(values: list[str]) -> dict[str, str]:
    if not values:
        return dict(DEFAULT_METHOD_FILES)
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected NAME=PATH, received {value!r}.")
        name, path = value.split("=", 1)
        if not name or not path:
            raise ValueError(f"Expected NAME=PATH, received {value!r}.")
        result[name] = path
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def answer_references(raw_answers: Any) -> list[dict[str, str]]:
    if not isinstance(raw_answers, dict):
        return []
    annotations = raw_answers.get("answer", [])
    references: list[dict[str, str]] = []
    for annotation in annotations if isinstance(annotations, list) else []:
        if not isinstance(annotation, dict):
            continue
        if annotation.get("unanswerable"):
            text, answer_type = "Unanswerable", "none"
        elif annotation.get("extractive_spans"):
            spans = [str(span).strip() for span in annotation["extractive_spans"]]
            text, answer_type = ", ".join(span for span in spans if span), "extractive"
        elif str(annotation.get("free_form_answer", "")).strip():
            text = str(annotation["free_form_answer"]).strip()
            answer_type = "abstractive"
        elif annotation.get("yes_no") is True:
            text, answer_type = "Yes", "boolean"
        elif annotation.get("yes_no") is False:
            text, answer_type = "No", "boolean"
        else:
            raise ValueError(f"Answer annotation has no recognized answer: {annotation}")
        references.append({"answer": text, "type": answer_type})
    return references


def evidence_blocks(
    units: list[dict[str, Any]], max_chars: int
) -> tuple[str, list[str], int]:
    blocks: list[str] = []
    unit_ids: list[str] = []
    total_chars = 0
    for unit in units:
        text = str(unit.get("text", "")).strip()
        if not text:
            continue
        block = (
            f"[Evidence {len(blocks) + 1}]\n"
            f"Type: {unit.get('unit_type', 'unknown')}\n"
            f"Section: {unit.get('section_name', 'Unknown section')}\n"
            f"Text: {text}\n"
        )
        if total_chars + len(block) > max_chars:
            break
        blocks.append(block)
        unit_ids.append(str(unit.get("unit_id", "")))
        total_chars += len(block)
    return "\n".join(blocks), unit_ids, total_chars


def build_prompt(title: str, question: str, evidence: str) -> str:
    return f"""You are answering a question about a research paper.

Use only the evidence below. Return the shortest answer that is fully supported by that evidence.

Rules:
- Copy exact names, values, and short phrases from the evidence when possible.
- If the question asks for several items, include every supported item concisely.
- For a yes/no question, answer "Yes" or "No" and add only a short qualifying phrase if needed.
- If the evidence does not support an answer, return exactly "Unanswerable".
- Do not use outside knowledge, cite evidence numbers, or explain your reasoning.

Paper title:
{title}

Question:
{question}

Evidence:
{evidence}

Answer:
"""


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    method_files = parse_method_files(args.method_file)

    papers = read_jsonl(str(input_path))
    ordered = sorted(papers, key=lambda paper: str(paper["paper_id"]))
    random.Random(args.seed).shuffle(ordered)

    selected: list[dict[str, Any]] = []
    selected_questions = 0
    for paper in ordered:
        if selected_questions >= args.min_questions:
            break
        selected.append(paper)
        selected_questions += len(paper.get("questions", []))
    if selected_questions < args.min_questions:
        raise ValueError(
            f"Only {selected_questions} questions available; requested {args.min_questions}."
        )

    selected_keys: list[tuple[str, str]] = []
    question_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    manifest_papers: list[dict[str, Any]] = []
    for sample_order, paper in enumerate(selected, start=1):
        paper_id = str(paper["paper_id"])
        question_ids: list[str] = []
        for question in paper.get("questions", []):
            question_id = str(question["question_id"])
            key = (paper_id, question_id)
            if key in question_metadata:
                raise ValueError(f"Duplicate processed question key: {key}")
            selected_keys.append(key)
            question_ids.append(question_id)
            question_metadata[key] = {
                "title": str(paper.get("title", "")),
                "question": str(question.get("question", "")),
                "reference_answers": answer_references(question.get("raw_answers")),
            }
        manifest_papers.append(
            {
                "sample_order": sample_order,
                "paper_id": paper_id,
                "question_count": len(question_ids),
                "question_ids": question_ids,
            }
        )

    manifest = {
        "status": "frozen_before_prompt_construction",
        "source_split": "official QASPER test",
        "sampling_unit": "paper",
        "algorithm": "sort paper IDs, shuffle with random.Random(seed), include whole papers until minimum question count",
        "seed": args.seed,
        "minimum_questions": args.min_questions,
        "selected_papers": len(selected),
        "selected_questions": len(selected_keys),
        "input_path": str(input_path),
        "input_sha256": sha256_file(input_path),
        "papers": manifest_papers,
    }
    manifest_path = output_dir / "test_generation_sample_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    question_manifest_path = output_dir / "test_generation_sample_questions.csv"
    with question_manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_order", "paper_id", "question_order", "question_id"],
        )
        writer.writeheader()
        order = 0
        for paper in manifest_papers:
            for question_order, question_id in enumerate(paper["question_ids"], start=1):
                order += 1
                writer.writerow(
                    {
                        "sample_order": order,
                        "paper_id": paper["paper_id"],
                        "question_order": question_order,
                        "question_id": question_id,
                    }
                )

    expected_key_set = set(selected_keys)
    prompt_records: list[dict[str, Any]] = []
    method_audit: dict[str, Any] = {}
    for method, filename in method_files.items():
        path = Path(filename)
        all_rows = read_jsonl(str(path))
        row_by_key = {
            (str(row["paper_id"]), str(row["question_id"])): row for row in all_rows
        }
        if len(row_by_key) != len(all_rows):
            raise ValueError(f"Duplicate method keys in {method}: {path}")
        missing = expected_key_set - set(row_by_key)
        if missing:
            raise ValueError(f"{method} is missing {len(missing)} sampled questions.")

        retained_counts: list[int] = []
        retained_chars: list[int] = []
        for paper_id, question_id in selected_keys:
            source = row_by_key[(paper_id, question_id)]
            metadata = question_metadata[(paper_id, question_id)]
            evidence, retained_unit_ids, evidence_chars = evidence_blocks(
                source.get("retrieved_units", []), args.max_evidence_chars
            )
            prompt = build_prompt(
                metadata["title"], metadata["question"], evidence
            )
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            retained_counts.append(len(retained_unit_ids))
            retained_chars.append(evidence_chars)
            prompt_records.append(
                {
                    "method": method,
                    "paper_id": paper_id,
                    "question_id": question_id,
                    "question": metadata["question"],
                    "reference_answers": metadata["reference_answers"],
                    "source_retrieved_units": len(source.get("retrieved_units", [])),
                    "retained_evidence_units": len(retained_unit_ids),
                    "retained_evidence_unit_ids": retained_unit_ids,
                    "retained_evidence_chars": evidence_chars,
                    "max_evidence_chars": args.max_evidence_chars,
                    "prompt_sha256": prompt_hash,
                    "prompt": prompt,
                }
            )
        method_audit[method] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "records": len(selected_keys),
            "mean_retained_units": sum(retained_counts) / len(retained_counts),
            "max_retained_units": max(retained_counts),
            "mean_retained_evidence_chars": sum(retained_chars) / len(retained_chars),
            "max_retained_evidence_chars": max(retained_chars),
            "truncated_questions": sum(
                record["source_retrieved_units"] > record["retained_evidence_units"]
                for record in prompt_records
                if record["method"] == method
            ),
        }

    prompts_path = output_dir / "test_generation_prompts.jsonl"
    write_jsonl(prompt_records, str(prompts_path))
    hash_counts = Counter(record["prompt_sha256"] for record in prompt_records)
    prompt_audit = {
        "status": "pass",
        "methods": list(method_files),
        "papers": len(selected),
        "questions": len(selected_keys),
        "method_question_records": len(prompt_records),
        "unique_prompts": len(hash_counts),
        "reused_method_question_records": sum(count - 1 for count in hash_counts.values()),
        "prompt_reuse_rate": 1.0 - len(hash_counts) / len(prompt_records),
        "max_prompt_reuse": max(hash_counts.values()),
        "max_evidence_chars": args.max_evidence_chars,
        "methods_audit": method_audit,
        "prompts_path": str(prompts_path),
        "prompts_sha256": sha256_file(prompts_path),
    }
    audit_path = output_dir / "test_generation_prompt_audit.json"
    audit_path.write_text(json.dumps(prompt_audit, indent=2) + "\n", encoding="utf-8")

    print(
        f"Frozen sample: {len(selected)} papers, {len(selected_keys)} questions; "
        f"manifest={manifest_path}"
    )
    print(
        f"Prompts: {len(prompt_records)} method-question records, "
        f"{len(hash_counts)} unique ({prompt_audit['prompt_reuse_rate']:.1%} reuse)"
    )
    for method, details in method_audit.items():
        print(
            f"{method:25s} mean_units={details['mean_retained_units']:.2f} "
            f"max_chars={details['max_retained_evidence_chars']} "
            f"truncated={details['truncated_questions']}"
        )


if __name__ == "__main__":
    main()
