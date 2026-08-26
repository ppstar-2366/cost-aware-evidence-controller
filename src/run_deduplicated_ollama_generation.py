from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate once per unique prompt hash and retain Ollama token counts."
    )
    parser.add_argument(
        "--input",
        default="outputs/supplementary/generation/test_generation_prompts.jsonl",
    )
    parser.add_argument(
        "--output",
        default="outputs/supplementary/generation/test_generation_unique_generations.jsonl",
    )
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--limit-questions", type=int)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def get_json(url: str, timeout: int = 10) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_ollama(base_url: str, model: str) -> dict[str, Any]:
    try:
        tags = get_json(f"{base_url}/api/tags")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base_url}; start the local server first."
        ) from exc
    model_names = {
        str(item.get("name", "")) for item in tags.get("models", [])
    } | {str(item.get("model", "")) for item in tags.get("models", [])}
    if model not in model_names:
        raise RuntimeError(
            f"Model {model!r} is not installed. Available models: {sorted(model_names)}"
        )
    return tags


def select_records(
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
    selected_keys = set(ordered_keys[:limit_questions])
    return [
        record
        for record in records
        if (str(record["paper_id"]), str(record["question_id"])) in selected_keys
    ]


def latest_by_hash(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {
        str(record["prompt_sha256"]): record
        for record in read_jsonl(str(path))
    }


def unique_prompts(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    by_hash: dict[str, dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    for record in records:
        prompt_hash = str(record["prompt_sha256"])
        prompt = str(record["prompt"])
        counts[prompt_hash] += 1
        if prompt_hash in by_hash:
            if str(by_hash[prompt_hash]["prompt"]) != prompt:
                raise ValueError(f"SHA-256 collision or inconsistent prompt: {prompt_hash}")
            continue
        by_hash[prompt_hash] = record
    return list(by_hash.values()), counts


def generate(
    prompt: str,
    model: str,
    base_url: str,
    timeout: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    seed: int,
) -> dict[str, Any]:
    return post_json(
        f"{base_url}/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": temperature,
                "seed": seed,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
        },
        timeout=timeout,
    )


def output_record(
    source: dict[str, Any],
    response: dict[str, Any] | None,
    model: str,
    status: str,
    elapsed: float,
    error: str,
    reuse_count: int,
) -> dict[str, Any]:
    response = response or {}
    return {
        "prompt_sha256": source["prompt_sha256"],
        "representative_method": source["method"],
        "representative_paper_id": source["paper_id"],
        "representative_question_id": source["question_id"],
        "method_question_reuse_count": reuse_count,
        "prompt_chars": len(source["prompt"]),
        "model": response.get("model", model),
        "status": status,
        "generated_answer": str(response.get("response", "")).strip(),
        "done": response.get("done", False),
        "done_reason": response.get("done_reason", ""),
        "prompt_eval_count": int(response.get("prompt_eval_count", 0)),
        "eval_count": int(response.get("eval_count", 0)),
        "total_duration_ns": int(response.get("total_duration", 0)),
        "load_duration_ns": int(response.get("load_duration", 0)),
        "prompt_eval_duration_ns": int(response.get("prompt_eval_duration", 0)),
        "eval_duration_ns": int(response.get("eval_duration", 0)),
        "wall_time_seconds": round(elapsed, 3),
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    args = parse_args()
    tags = check_ollama(args.base_url, args.model)
    input_records = read_jsonl(args.input)
    selected_records = select_records(input_records, args.limit_questions)
    unique_records, reuse_counts = unique_prompts(selected_records)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = latest_by_hash(output_path)
    pending = [
        record
        for record in unique_records
        if completed.get(str(record["prompt_sha256"]), {}).get("status") != "ok"
    ]

    question_keys = {
        (str(record["paper_id"]), str(record["question_id"]))
        for record in selected_records
    }
    methods = sorted({str(record["method"]) for record in selected_records})
    print(f"Model: {args.model}")
    print(
        f"Selected: {len(question_keys)} questions × {len(methods)} methods = "
        f"{len(selected_records)} method-question records"
    )
    print(
        f"Unique prompts: {len(unique_records)}; already completed: "
        f"{len(unique_records) - len(pending)}; pending: {len(pending)}"
    )

    with output_path.open("a", encoding="utf-8", buffering=1) as handle:
        for index, record in enumerate(pending, start=1):
            response: dict[str, Any] | None = None
            last_error = ""
            started = time.perf_counter()
            for attempt in range(1, args.retries + 1):
                try:
                    response = generate(
                        prompt=str(record["prompt"]),
                        model=args.model,
                        base_url=args.base_url,
                        timeout=args.timeout,
                        num_ctx=args.num_ctx,
                        num_predict=args.num_predict,
                        temperature=args.temperature,
                        seed=args.seed,
                    )
                    break
                except (
                    urllib.error.URLError,
                    TimeoutError,
                    json.JSONDecodeError,
                ) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < args.retries:
                        time.sleep(min(2**attempt, 10))
            elapsed = time.perf_counter() - started
            status = "ok" if response is not None else "error"
            result = output_record(
                source=record,
                response=response,
                model=args.model,
                status=status,
                elapsed=elapsed,
                error=last_error,
                reuse_count=reuse_counts[str(record["prompt_sha256"])],
            )
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(
                f"[{index}/{len(pending)}] {record['prompt_sha256'][:10]} "
                f"reuse={result['method_question_reuse_count']} status={status} "
                f"tokens={result['prompt_eval_count']}+{result['eval_count']} "
                f"time={elapsed:.1f}s"
            )

    latest = latest_by_hash(output_path)
    selected_latest = {
        str(record["prompt_sha256"]): latest.get(str(record["prompt_sha256"]), {})
        for record in unique_records
    }
    ok = [record for record in selected_latest.values() if record.get("status") == "ok"]
    errors = [
        prompt_hash
        for prompt_hash, record in selected_latest.items()
        if record.get("status") != "ok"
    ]
    prompt_tokens = [int(record.get("prompt_eval_count", 0)) for record in ok]
    audit = {
        "status": "pass" if not errors else "fail",
        "mode": "smoke" if args.limit_questions is not None else "frozen_sample",
        "input": args.input,
        "output": args.output,
        "methods": methods,
        "papers": len({str(record["paper_id"]) for record in selected_records}),
        "questions": len(question_keys),
        "method_question_records": len(selected_records),
        "unique_prompts": len(unique_records),
        "prompt_reuse_rate": 1.0 - len(unique_records) / len(selected_records),
        "successful_unique_prompts": len(ok),
        "failed_unique_prompts": len(errors),
        "failed_hashes": errors,
        "model": args.model,
        "model_inventory": tags.get("models", []),
        "options": {
            "temperature": args.temperature,
            "seed": args.seed,
            "num_ctx": args.num_ctx,
            "num_predict": args.num_predict,
        },
        "prompt_tokens": {
            "mean": sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0.0,
            "maximum": max(prompt_tokens, default=0),
            "context_limit": args.num_ctx,
            "maximum_fraction_of_context": (
                max(prompt_tokens, default=0) / args.num_ctx if args.num_ctx else 0.0
            ),
        },
    }
    audit_path = output_path.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Saved unique generations to {output_path}")
    print(f"Audit status: {audit['status']}; saved to {audit_path}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
