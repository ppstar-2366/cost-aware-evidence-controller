from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import read_jsonl


EXPECTED_METHODS = {
    "ControllerV3",
    "BM25_top7",
    "BM25_top8",
    "ControllerV3_no_section",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the frozen paper sample, prompts, and deduplicated generations."
    )
    parser.add_argument(
        "--prompts",
        default="outputs/supplementary/generation/test_generation_prompts.jsonl",
    )
    parser.add_argument(
        "--generations",
        default="outputs/supplementary/generation/test_generation_unique_generations.jsonl",
    )
    parser.add_argument(
        "--manifest",
        default="outputs/supplementary/generation/test_generation_sample_manifest.json",
    )
    parser.add_argument("--output-dir", default="outputs/supplementary/generation")
    parser.add_argument("--prefix", default="test_generation")
    parser.add_argument("--limit-questions", type=int)
    parser.add_argument("--expected-questions", type=int, default=201)
    parser.add_argument("--max-evidence-chars", type=int, default=20000)
    parser.add_argument("--num-ctx", type=int, default=8192)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_records(
    records: list[dict[str, Any]], limit_questions: int | None
) -> list[dict[str, Any]]:
    if limit_questions is None:
        return records
    ordered: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (str(record["paper_id"]), str(record["question_id"]))
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    selected = set(ordered[:limit_questions])
    return [
        record
        for record in records
        if (str(record["paper_id"]), str(record["question_id"])) in selected
    ]


def main() -> None:
    args = parse_args()
    prompt_path = Path(args.prompts)
    generation_path = Path(args.generations)
    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("seed") != 42:
        errors.append(f"Sample seed is {manifest.get('seed')!r}, expected 42.")
    if manifest.get("selected_questions") != args.expected_questions:
        errors.append(
            f"Manifest has {manifest.get('selected_questions')} questions; "
            f"expected {args.expected_questions}."
        )

    all_prompts = read_jsonl(str(prompt_path))
    prompts = select_records(all_prompts, args.limit_questions)
    methods = {str(record["method"]) for record in prompts}
    if methods != EXPECTED_METHODS:
        errors.append(f"Method set differs: {sorted(methods)}")
    question_keys = {
        (str(record["paper_id"]), str(record["question_id"])) for record in prompts
    }
    expected_selected_questions = args.limit_questions or args.expected_questions
    if len(question_keys) != expected_selected_questions:
        errors.append(
            f"Selected prompt set has {len(question_keys)} questions; "
            f"expected {expected_selected_questions}."
        )
    if len(prompts) != len(question_keys) * len(EXPECTED_METHODS):
        errors.append(f"Prompt set has {len(prompts)} method-question rows.")

    keys_by_method: dict[str, set[tuple[str, str]]] = {}
    for method in methods:
        keys = [
            (str(record["paper_id"]), str(record["question_id"]))
            for record in prompts
            if record["method"] == method
        ]
        if len(keys) != len(set(keys)):
            errors.append(f"Duplicate prompt keys for {method}.")
        keys_by_method[method] = set(keys)
        if set(keys) != question_keys:
            errors.append(f"Question alignment differs for {method}.")

    allowed_types = {"extractive", "abstractive", "boolean", "none"}
    recomputed_hashes: list[str] = []
    for record in prompts:
        prompt_hash = hashlib.sha256(str(record["prompt"]).encode("utf-8")).hexdigest()
        recomputed_hashes.append(prompt_hash)
        if prompt_hash != record["prompt_sha256"]:
            errors.append(
                f"Prompt hash mismatch for {record['method']}:{record['question_id']}."
            )
        if int(record["retained_evidence_chars"]) > args.max_evidence_chars:
            errors.append(f"Evidence character limit exceeded for {record['question_id']}.")
        if int(record["retained_evidence_units"]) > int(record["source_retrieved_units"]):
            errors.append(f"Retained-unit count exceeds source for {record['question_id']}.")
        references = record.get("reference_answers", [])
        if not references:
            errors.append(f"No reference answers for {record['question_id']}.")
        invalid_types = {
            str(reference.get("type")) for reference in references
        } - allowed_types
        if invalid_types:
            errors.append(
                f"Invalid reference types for {record['question_id']}: {invalid_types}"
            )

    hash_counts = Counter(recomputed_hashes)
    latest_generations: dict[str, dict[str, Any]] = {}
    raw_generation_count = 0
    if generation_path.exists():
        generation_records = read_jsonl(str(generation_path))
        raw_generation_count = len(generation_records)
        latest_generations = {
            str(record["prompt_sha256"]): record for record in generation_records
        }
    expected_hashes = set(hash_counts)
    missing_hashes = expected_hashes - set(latest_generations)
    unexpected_hashes = set(latest_generations) - expected_hashes
    failed_hashes = {
        prompt_hash
        for prompt_hash in expected_hashes & set(latest_generations)
        if latest_generations[prompt_hash].get("status") != "ok"
    }
    length_stopped_hashes = {
        prompt_hash
        for prompt_hash in expected_hashes & set(latest_generations)
        if latest_generations[prompt_hash].get("status") == "ok"
        and latest_generations[prompt_hash].get("done_reason") == "length"
    }
    if missing_hashes:
        errors.append(f"Missing {len(missing_hashes)} unique generations.")
    if unexpected_hashes:
        errors.append(f"Found {len(unexpected_hashes)} unexpected generation hashes.")
    if failed_hashes:
        errors.append(f"Found {len(failed_hashes)} failed unique generations.")
    if length_stopped_hashes:
        errors.append(
            f"Found {len(length_stopped_hashes)} length-stopped unique generations."
        )

    prompt_tokens = [
        int(latest_generations[prompt_hash].get("prompt_eval_count", 0))
        for prompt_hash in expected_hashes & set(latest_generations)
        if latest_generations[prompt_hash].get("status") == "ok"
    ]
    max_prompt_tokens = max(prompt_tokens, default=0)
    output_tokens = [
        int(latest_generations[prompt_hash].get("eval_count", 0))
        for prompt_hash in expected_hashes & set(latest_generations)
        if latest_generations[prompt_hash].get("status") == "ok"
    ]
    max_output_tokens = max(output_tokens, default=0)
    hypothetical_prompt_tokens = sum(
        int(
            latest_generations.get(str(record["prompt_sha256"]), {}).get(
                "prompt_eval_count", 0
            )
        )
        for record in prompts
    )
    hypothetical_output_tokens = sum(
        int(
            latest_generations.get(str(record["prompt_sha256"]), {}).get(
                "eval_count", 0
            )
        )
        for record in prompts
    )
    if max_prompt_tokens >= args.num_ctx:
        errors.append(
            f"Maximum prompt tokens {max_prompt_tokens} reaches context {args.num_ctx}."
        )

    mode = "smoke" if args.limit_questions is not None else "frozen_sample"
    audit = {
        "status": "pass" if not errors else "fail",
        "mode": mode,
        "sample_manifest": str(manifest_path),
        "sample_seed": manifest.get("seed"),
        "sample_papers": manifest.get("selected_papers"),
        "sample_questions": manifest.get("selected_questions"),
        "selected_questions": len(question_keys),
        "methods": sorted(methods),
        "method_question_records": len(prompts),
        "unique_prompts": len(expected_hashes),
        "reused_method_question_records": sum(count - 1 for count in hash_counts.values()),
        "prompt_reuse_rate": 1.0 - len(expected_hashes) / len(prompts),
        "raw_generation_records": raw_generation_count,
        "latest_unique_generation_records": len(latest_generations),
        "successful_complete_expected_unique_generations": len(
            expected_hashes
            - missing_hashes
            - failed_hashes
            - length_stopped_hashes
        ),
        "missing_unique_generations": len(missing_hashes),
        "unexpected_unique_generations": len(unexpected_hashes),
        "failed_unique_generations": len(failed_hashes),
        "length_stopped_unique_generations": len(length_stopped_hashes),
        "max_retained_evidence_chars": max(
            (int(record["retained_evidence_chars"]) for record in prompts), default=0
        ),
        "max_prompt_tokens": max_prompt_tokens,
        "max_output_tokens": max_output_tokens,
        "actual_unique_call_prompt_tokens": sum(prompt_tokens),
        "actual_unique_call_output_tokens": sum(output_tokens),
        "hypothetical_method_question_prompt_tokens": hypothetical_prompt_tokens,
        "hypothetical_method_question_output_tokens": hypothetical_output_tokens,
        "prompt_tokens_avoided_by_deduplication": (
            hypothetical_prompt_tokens - sum(prompt_tokens)
        ),
        "output_tokens_avoided_by_deduplication": (
            hypothetical_output_tokens - sum(output_tokens)
        ),
        "num_ctx": args.num_ctx,
        "errors": errors,
    }
    audit_path = output_dir / f"{args.prefix}_integrity_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    artifact_paths = [
        manifest_path,
        prompt_path,
        generation_path,
        Path("src/build_test_generation_sample.py"),
        Path("src/run_deduplicated_ollama_generation.py"),
        Path("src/evaluate_test_generation.py"),
        Path("src/audit_test_generation.py"),
        Path("src/common.py"),
        Path("requirements.txt"),
        Path("docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md"),
    ]
    manifest_rows = []
    for path in artifact_paths:
        if not path.exists():
            errors.append(f"Missing manifest artifact: {path}")
            continue
        manifest_rows.append(
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    sha_path = output_dir / f"{args.prefix}_sha256_manifest.csv"
    with sha_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    if errors and audit["status"] == "pass":
        audit["status"] = "fail"
        audit["errors"] = errors
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Generation audit status: {audit['status']}")
    print(
        f"Questions: {len(question_keys)}; method records: {len(prompts)}; "
        f"unique prompts: {len(expected_hashes)}"
    )
    print(f"Maximum prompt tokens: {max_prompt_tokens}/{args.num_ctx}")
    print(
        f"Maximum output tokens: {max_output_tokens}; "
        f"length stops: {len(length_stopped_hashes)}"
    )
    print(f"Saved audit to {audit_path}")
    print(f"Saved SHA-256 manifest to {sha_path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
