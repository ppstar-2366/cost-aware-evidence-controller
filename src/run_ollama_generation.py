import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


DEFAULT_INPUT = "outputs/generation_prompts_validation50.jsonl"
DEFAULT_OUTPUT = "outputs/ollama_generations_validation50.jsonl"
DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_URL = "http://127.0.0.1:11434"


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def completed_keys(path: str) -> Set[Tuple[str, str]]:
    output_path = Path(path)
    if not output_path.exists():
        return set()

    completed = set()
    for record in read_jsonl(path):
        if record.get("status") == "ok":
            completed.add((record.get("method", ""), record.get("question_id", "")))
    return completed


def post_json(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_ollama(base_url: str, timeout: int = 10) -> None:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Ollama health check returned HTTP {response.status}.")
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "Cannot connect to Ollama. Start Ollama and confirm that "
            f"{base_url}/api/tags is reachable."
        ) from error


def generate_once(
    prompt: str,
    model: str,
    base_url: str,
    timeout: int,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    seed: int,
) -> Dict[str, Any]:
    payload = {
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
    }
    return post_json(f"{base_url}/api/generate", payload, timeout=timeout)


def select_records(
    records: Iterable[Dict[str, Any]],
    methods: Optional[Set[str]],
    limit: Optional[int],
    limit_per_method: Optional[int],
) -> List[Dict[str, Any]]:
    selected = [record for record in records if not methods or record.get("method") in methods]
    if limit_per_method is not None:
        method_counts: Dict[str, int] = {}
        limited = []
        for record in selected:
            method = record.get("method", "")
            count = method_counts.get(method, 0)
            if count >= limit_per_method:
                continue
            limited.append(record)
            method_counts[method] = count + 1
        selected = limited
    if limit is not None:
        selected = selected[:limit]
    return selected


def build_output_record(
    source: Dict[str, Any],
    model: str,
    status: str,
    wall_time_seconds: float,
    response: Optional[Dict[str, Any]] = None,
    error: str = "",
) -> Dict[str, Any]:
    response = response or {}
    return {
        "method": source.get("method", ""),
        "paper_id": source.get("paper_id", ""),
        "question_id": source.get("question_id", ""),
        "question": source.get("question", ""),
        "reference_answers": source.get("reference_answers", []),
        "gold_evidence": source.get("gold_evidence", []),
        "num_retrieved_units": source.get("num_retrieved_units", 0),
        "model": response.get("model", model),
        "status": status,
        "generated_answer": response.get("response", "").strip(),
        "done_reason": response.get("done_reason", ""),
        "prompt_eval_count": response.get("prompt_eval_count", 0),
        "eval_count": response.get("eval_count", 0),
        "total_duration_ns": response.get("total_duration", 0),
        "load_duration_ns": response.get("load_duration", 0),
        "prompt_eval_duration_ns": response.get("prompt_eval_duration", 0),
        "eval_duration_ns": response.get("eval_duration", 0),
        "wall_time_seconds": round(wall_time_seconds, 3),
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate QASPER answers with a local Ollama model.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    parser.add_argument("--methods", nargs="+", help="Optional method names to run.")
    parser.add_argument("--limit", type=int, help="Run only the first N selected prompts.")
    parser.add_argument(
        "--limit-per-method",
        type=int,
        help="Run only the first N prompts from every selected method.",
    )
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_ollama(args.base_url)

    records = read_jsonl(args.input)
    methods = set(args.methods) if args.methods else None
    records = select_records(
        records,
        methods=methods,
        limit=args.limit,
        limit_per_method=args.limit_per_method,
    )
    completed = completed_keys(args.output)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pending = [
        record
        for record in records
        if (record.get("method", ""), record.get("question_id", "")) not in completed
    ]

    print(f"Model: {args.model}")
    print(f"Selected prompts: {len(records)}")
    print(f"Already completed: {len(records) - len(pending)}")
    print(f"Pending: {len(pending)}")

    with open(output_path, "a", encoding="utf-8", buffering=1) as output_file:
        for index, record in enumerate(pending, start=1):
            response = None
            last_error = ""
            started = time.perf_counter()

            for attempt in range(1, args.retries + 1):
                try:
                    response = generate_once(
                        prompt=record["prompt"],
                        model=args.model,
                        base_url=args.base_url,
                        timeout=args.timeout,
                        num_ctx=args.num_ctx,
                        num_predict=args.num_predict,
                        temperature=args.temperature,
                        seed=args.seed,
                    )
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                    last_error = f"{type(error).__name__}: {error}"
                    if attempt < args.retries:
                        time.sleep(min(2 ** attempt, 10))

            elapsed = time.perf_counter() - started
            status = "ok" if response is not None else "error"
            result = build_output_record(
                source=record,
                model=args.model,
                status=status,
                wall_time_seconds=elapsed,
                response=response,
                error=last_error,
            )
            output_file.write(json.dumps(result, ensure_ascii=False) + "\n")

            prompt_tokens = result["prompt_eval_count"]
            answer_tokens = result["eval_count"]
            print(
                f"[{index}/{len(pending)}] {record['method']} "
                f"{record['question_id'][:10]} status={status} "
                f"tokens={prompt_tokens}+{answer_tokens} time={elapsed:.1f}s"
            )

    print(f"Saved generations to {output_path}")


if __name__ == "__main__":
    main()
