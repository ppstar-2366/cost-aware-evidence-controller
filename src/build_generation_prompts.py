import argparse
from typing import List, Dict, Any

from common import read_jsonl, write_jsonl


DEFAULT_METHOD_FILES = {
    "BM25_top5": "outputs/validation50_bm25_top5.jsonl",
    "BM25_top10": "outputs/validation50_bm25_top10.jsonl",
    "BM25_top20": "outputs/validation50_bm25_top20.jsonl",
    "ControllerV3": "outputs/validation50_controller_v3.jsonl",
}


MAX_EVIDENCE_CHARS = 6000


def format_evidence(retrieved_units: List[Dict[str, Any]]) -> str:
    parts = []
    total_chars = 0

    for i, unit in enumerate(retrieved_units, start=1):
        unit_type = unit.get("unit_type", "unknown")
        section = unit.get("section_name", "Unknown section")
        text = unit.get("text", "").strip()

        if not text:
            continue

        block = (
            f"[Evidence {i}]\n"
            f"Type: {unit_type}\n"
            f"Section: {section}\n"
            f"Text: {text}\n"
        )

        if total_chars + len(block) > MAX_EVIDENCE_CHARS:
            break

        parts.append(block)
        total_chars += len(block)

    return "\n".join(parts)


def build_prompt(item: Dict[str, Any]) -> str:
    title = item.get("title", "")
    question = item.get("question", "")
    evidence_text = format_evidence(item.get("retrieved_units", []))

    prompt = f"""You are answering a question about a research paper.

Use only the evidence provided below. The evidence was retrieved from the paper and often contains the answer.
Your job is to extract the shortest correct answer from the evidence.

Important rules:
- Prefer answering with words or phrases copied from the evidence.
- If the question asks "which" or "what", list the relevant methods, datasets, models, metrics, or findings.
- If the evidence partially answers the question, give the best supported partial answer.
- Say "Not enough evidence." only when the evidence is clearly unrelated to the question.
- Do not use outside knowledge.

Paper title:
{title}

Question:
{question}

Evidence:
{evidence_text}

Return only the answer text. Do not include explanations, citations, or evidence numbers.
Answer:
"""

    return prompt


def parse_method_files(values: List[str]) -> Dict[str, str]:
    method_files: Dict[str, str] = {}

    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid method mapping: {value}. Expected NAME=PATH.")

        method, path = value.split("=", 1)
        method_files[method] = path

    return method_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build answer-generation prompts from retrieval outputs.")
    parser.add_argument("--output", default="outputs/generation_prompts_validation50.jsonl")
    parser.add_argument(
        "--method-file",
        action="append",
        default=[],
        help="Method mapping in NAME=PATH format. Can be supplied multiple times.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    method_files = parse_method_files(args.method_file) if args.method_file else DEFAULT_METHOD_FILES
    all_prompt_records = []

    for method_name, path in method_files.items():
        print(f"Loading {method_name}: {path}")

        records = read_jsonl(path)

        for item in records:
            prompt = build_prompt(item)

            all_prompt_records.append(
                {
                    "method": method_name,
                    "paper_id": item["paper_id"],
                    "question_id": item["question_id"],
                    "question": item["question"],
                    "reference_answers": item.get("reference_answers", []),
                    "gold_evidence": item.get("gold_evidence", []),
                    "num_retrieved_units": len(item.get("retrieved_units", [])),
                    "prompt": prompt,
                }
            )

    output_path = args.output
    write_jsonl(all_prompt_records, output_path)

    print(f"\nSaved prompts to {output_path}")
    print(f"Total prompts: {len(all_prompt_records)}")

    print("\nFirst prompt preview:")
    print("=" * 80)
    print(all_prompt_records[0]["prompt"][:2000])


if __name__ == "__main__":
    main()
