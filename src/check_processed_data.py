import argparse
from collections import Counter

from common import read_jsonl


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect a processed QASPER JSONL file.")
    parser.add_argument("--input", default="data/processed/qasper_train_100.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    records = read_jsonl(args.input)

    print("Input:", args.input)
    print("Loaded papers:", len(records))

    total_units = sum(len(record["evidence_units"]) for record in records)
    total_questions = sum(len(record["questions"]) for record in records)

    print("Total evidence units:", total_units)
    print("Total questions:", total_questions)

    unit_type_counter = Counter()

    for record in records:
        for unit in record["evidence_units"]:
            unit_type_counter[unit["unit_type"]] += 1

    print("\nEvidence unit type counts:")
    for unit_type, count in unit_type_counter.most_common():
        print(f"{unit_type}: {count}")

    first = records[0]

    print("\nFirst paper:")
    print("paper_id:", first["paper_id"])
    print("title:", first["title"])
    print("num_units:", first["num_units"])
    print("num_questions:", first["num_questions"])

    print("\nFirst 3 evidence units:")
    for unit in first["evidence_units"][:3]:
        print("\n---")
        print("unit_id:", unit["unit_id"])
        print("unit_type:", unit["unit_type"])
        print("section_name:", unit["section_name"])
        print("word_count:", unit["word_count"])
        print("text:", unit["text"][:300])

    print("\nFirst 3 questions:")
    for q in first["questions"][:3]:
        print("\n---")
        print("question_id:", q["question_id"])
        print("question:", q["question"])
        print("raw_answers type:", type(q["raw_answers"]))
        print("raw_answers preview:", str(q["raw_answers"])[:500])


if __name__ == "__main__":
    main()
