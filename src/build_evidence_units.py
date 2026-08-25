from datasets import load_dataset
from pathlib import Path
from typing import Any, Dict, List
import argparse
import json
import re
from tqdm import tqdm


def normalise_text(value: Any) -> str:
    """
    Convert QASPER fields into clean text.
    QASPER may store text as strings, lists, or nested lists.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return " ".join(value.split())

    if isinstance(value, list):
        parts = []
        for item in value:
            text = normalise_text(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = normalise_text(item)
            if text:
                parts.append(f"{key}: {text}")
        return "\n".join(parts).strip()

    return str(value).strip()


def chunk_text(text: str, max_words: int = 250, overlap: int = 40) -> List[str]:
    """
    Split a long text into overlapping chunks.
    This is intentionally simple for the first version.
    """
    words = text.split()

    if not words:
        return []

    if len(words) <= max_words:
        return [" ".join(words)]

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = max(0, end - overlap)

    return chunks


def classify_caption(caption: str) -> str:
    """
    Classify a QASPER figure/table caption into table or figure_caption.
    """
    caption_lower = caption.lower().strip()

    if re.match(r"^table\s*\d*", caption_lower):
        return "table"

    if re.match(r"^figure\s*\d*", caption_lower) or re.match(r"^fig\.\s*\d*", caption_lower):
        return "figure_caption"

    if "table" in caption_lower[:30]:
        return "table"

    if "figure" in caption_lower[:30] or "fig." in caption_lower[:30]:
        return "figure_caption"

    return "figure_table"


def add_unit(
    units: List[Dict[str, Any]],
    paper_id: str,
    unit_type: str,
    section_name: str,
    text: str,
    position: int,
    source_id: str = "",
):
    text = normalise_text(text)

    if not text:
        return

    unit_id = f"{paper_id}_{unit_type}_{len(units)}"

    units.append(
        {
            "paper_id": paper_id,
            "unit_id": unit_id,
            "unit_type": unit_type,
            "section_name": section_name,
            "text": text,
            "position": position,
            "source_id": source_id,
            "word_count": len(text.split()),
        }
    )


def extract_title_and_abstract(example: Dict[str, Any], units: List[Dict[str, Any]]):
    paper_id = example["id"]

    title = normalise_text(example.get("title", ""))
    if title:
        add_unit(
            units=units,
            paper_id=paper_id,
            unit_type="title",
            section_name="Title",
            text=title,
            position=len(units),
        )

    abstract = normalise_text(example.get("abstract", ""))
    if abstract:
        add_unit(
            units=units,
            paper_id=paper_id,
            unit_type="abstract",
            section_name="Abstract",
            text=abstract,
            position=len(units),
        )


def extract_full_text(example: Dict[str, Any], units: List[Dict[str, Any]]):
    paper_id = example["id"]
    full_text = example.get("full_text", {})

    if not isinstance(full_text, dict):
        return

    section_names = full_text.get("section_name", [])
    paragraphs = full_text.get("paragraphs", [])

    for section_index, (section_name, section_paragraphs) in enumerate(zip(section_names, paragraphs)):
        section_name = normalise_text(section_name) or f"Section {section_index}"

        section_text = normalise_text(section_paragraphs)

        for chunk_index, chunk in enumerate(chunk_text(section_text)):
            add_unit(
                units=units,
                paper_id=paper_id,
                unit_type="chunk",
                section_name=section_name,
                text=chunk,
                position=len(units),
                source_id=f"section_{section_index}_chunk_{chunk_index}",
            )


def extract_figures_and_tables(example: Dict[str, Any], units: List[Dict[str, Any]]):
    paper_id = example["id"]
    figures_and_tables = example.get("figures_and_tables", {})

    if not isinstance(figures_and_tables, dict):
        return

    captions = figures_and_tables.get("caption", [])
    files = figures_and_tables.get("file", [])

    for i, caption in enumerate(captions):
        caption_text = normalise_text(caption)

        if not caption_text:
            continue

        unit_type = classify_caption(caption_text)
        file_name = files[i] if i < len(files) else ""

        add_unit(
            units=units,
            paper_id=paper_id,
            unit_type=unit_type,
            section_name="Figures and Tables",
            text=caption_text,
            position=len(units),
            source_id=str(file_name),
        )


def extract_questions(example: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract questions and answer metadata from QASPER.
    We keep the raw answers for now because we will inspect exact answer format later.
    """
    qas = example.get("qas", {})

    questions = qas.get("question", [])
    question_ids = qas.get("question_id", [])
    answers = qas.get("answers", [])

    output = []

    for i, question in enumerate(questions):
        qid = question_ids[i] if i < len(question_ids) else f"{example['id']}_q{i}"
        raw_answers = answers[i] if i < len(answers) else None

        output.append(
            {
                "paper_id": example["id"],
                "question_id": qid,
                "question": normalise_text(question),
                "raw_answers": raw_answers,
            }
        )

    return output


def build_paper_record(example: Dict[str, Any]) -> Dict[str, Any]:
    units = []

    extract_title_and_abstract(example, units)
    extract_full_text(example, units)
    extract_figures_and_tables(example, units)

    questions = extract_questions(example)

    return {
        "paper_id": example["id"],
        "title": normalise_text(example.get("title", "")),
        "evidence_units": units,
        "questions": questions,
        "num_units": len(units),
        "num_questions": len(questions),
    }


def write_jsonl(records: List[Dict[str, Any]], output_path: str):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_split(dataset, split_name: str, max_papers: int = None, output_path: str = None):
    print(f"\nProcessing split: {split_name}")
    split = dataset[split_name]

    if max_papers is not None:
        split = split.select(range(min(max_papers, len(split))))

    records = []

    for example in tqdm(split):
        record = build_paper_record(example)
        records.append(record)

    if output_path is None:
        suffix = f"{max_papers}" if max_papers is not None else "full"
        output_path = f"data/processed/qasper_{split_name}_{suffix}.jsonl"

    write_jsonl(records, output_path)

    total_units = sum(record["num_units"] for record in records)
    total_questions = sum(record["num_questions"] for record in records)

    print(f"Saved to {output_path}")
    print(f"Papers: {len(records)}")
    print(f"Evidence units: {total_units}")
    print(f"Questions: {total_questions}")


def parse_args():
    parser = argparse.ArgumentParser(description="Build structured evidence units from QASPER.")
    parser.add_argument("--train-papers", type=int, default=100)
    parser.add_argument("--validation-papers", type=int, default=50)
    parser.add_argument("--train-output", default="data/processed/qasper_train_100.jsonl")
    parser.add_argument("--validation-output", default="data/processed/qasper_validation_50.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Loading QASPER...")
    dataset = load_dataset("allenai/qasper", trust_remote_code=True)

    Path("data/processed").mkdir(parents=True, exist_ok=True)

    process_split(
        dataset,
        "train",
        max_papers=args.train_papers,
        output_path=args.train_output,
    )
    process_split(
        dataset,
        "validation",
        max_papers=args.validation_papers,
        output_path=args.validation_output,
    )


if __name__ == "__main__":
    main()
