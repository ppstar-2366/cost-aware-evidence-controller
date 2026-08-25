from typing import List, Dict, Any, Tuple
from tqdm import tqdm

from common import (
    extract_gold_evidence,
    extract_reference_answers,
    read_jsonl,
    write_csv,
    write_jsonl,
)
from retrieval import (
    add_unique_units,
    classify_question,
    compute_cost_stats,
    evaluate_predictions,
    get_retrievable_units,
    rank_units,
)


def enhanced_classify_question(question: str) -> Dict[str, bool]:
    """
    Extend the v1 classifier with a few patterns found in error analysis.
    """
    qtype = classify_question(question)
    q = question.lower()

    data_patterns = [
        "dataset",
        "datasets",
        "data set",
        "corpus",
        "corpora",
        "language pair",
        "language pairs",
        "languages",
        "training data",
        "test set",
        "development set",
        "experiment with",
        "used for training",
    ]

    abbreviation_patterns = [
        "abbreviate",
        "abbreviation",
        "stand for",
        "stands for",
        "what does",
        "what is",
    ]

    if any(pattern in q for pattern in data_patterns):
        qtype["is_data"] = True

    qtype["is_abbreviation"] = any(pattern in q for pattern in abbreviation_patterns) and (
        "abbreviate" in q
        or "stand for" in q
        or "stands for" in q
        or "what does" in q
    )

    if qtype["is_abbreviation"]:
        qtype["is_definition"] = True

    return qtype


def build_definition_query(question: str) -> str:
    definition_terms = [
        "definition",
        "defined",
        "means",
        "refers",
        "called",
        "consists",
        "consists of",
        "stands for",
        "abbreviation",
    ]

    return question + " " + " ".join(definition_terms)


def build_data_query(question: str) -> str:
    data_terms = [
        "dataset",
        "datasets",
        "data",
        "corpus",
        "corpora",
        "experimental setup",
        "experiments",
        "training",
        "test",
        "development",
        "language pairs",
        "languages",
        "used",
    ]

    return question + " " + " ".join(data_terms)


def section_contains(unit: Dict[str, Any], keywords: List[str]) -> bool:
    section = unit.get("section_name", "").lower()
    text = unit.get("text", "").lower()[:500]

    return any(keyword in section or keyword in text for keyword in keywords)


def rank_section_aware_units(
    question: str,
    units: List[Dict[str, Any]],
    section_keywords: List[str],
    expanded_query: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    """
    Rank only units from likely relevant sections.
    If no section-aware candidates are found, return an empty list.
    """
    candidates = [
        unit for unit in units
        if unit.get("unit_type") in {"abstract", "chunk", "table", "figure_caption"}
        and section_contains(unit, section_keywords)
    ]

    if not candidates:
        return []

    return rank_units(
        question=expanded_query,
        units=candidates,
        top_k=min(top_k, len(candidates)),
    )


def run_controller_for_question_v3(
    question: str,
    evidence_units: List[Dict[str, Any]],
    use_section_expansion: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, bool]]:
    """
    Controller v3.

    Main differences from v1/v2:
    - Dataset and language-pair questions receive section-aware retrieval
      from Data / Dataset / Experimental Setup sections.
    - Definition and abbreviation questions receive introduction-focused retrieval.
    """
    qtype = enhanced_classify_question(question)

    retrievable_units = get_retrievable_units(evidence_units)

    ranked_all = rank_units(
        question=question,
        units=retrievable_units,
        top_k=min(20, len(retrievable_units)),
    )

    table_units = [
        unit for unit in retrievable_units
        if unit.get("unit_type") == "table"
    ]

    figure_units = [
        unit for unit in retrievable_units
        if unit.get("unit_type") == "figure_caption"
    ]

    ranked_tables = rank_units(
        question=question,
        units=table_units,
        top_k=min(3, len(table_units)),
    )

    ranked_figures = rank_units(
        question=question,
        units=figure_units,
        top_k=min(2, len(figure_units)),
    )

    selected = []
    actions = []

    added = add_unique_units(
        selected=selected,
        candidates=ranked_all[:3],
        selected_by="ReadTop3",
    )

    actions.append(
        {
            "action": "ReadTop3",
            "added_units": added,
            "reason": "Start with a small set of high-ranked evidence units.",
        }
    )

    # Definition / abbreviation questions.
    if qtype["is_definition"]:
        definition_query = build_definition_query(question)

        definition_section_units = []

        if use_section_expansion:
            definition_section_units = rank_section_aware_units(
                question=question,
                units=retrievable_units,
                section_keywords=[
                    "abstract",
                    "introduction",
                    "background",
                    "overview",
                ],
                expanded_query=definition_query,
                top_k=4,
            )

        added_intro_definition = add_unique_units(
            selected=selected,
            candidates=definition_section_units,
            selected_by="DefinitionIntroExpansion",
            max_new=2,
        )

        if added_intro_definition > 0:
            actions.append(
                {
                    "action": "DefinitionIntroExpansion",
                    "added_units": added_intro_definition,
                    "reason": "Definition or abbreviation question; introduction and abstract are likely to define the term.",
                }
            )

        # Fallback to all-section definition expansion if introduction did not add enough.
        if added_intro_definition < 1:
            all_definition_units = rank_units(
                question=definition_query,
                units=retrievable_units,
                top_k=min(8, len(retrievable_units)),
            )

            added_definition = add_unique_units(
                selected=selected,
                candidates=all_definition_units,
                selected_by="DefinitionExpansion",
                max_new=2,
            )

            actions.append(
                {
                    "action": "DefinitionExpansion",
                    "added_units": added_definition,
                    "reason": "Fallback definition-focused search over all evidence units.",
                }
            )

        actions.append(
            {
                "action": "Stop",
                "added_units": 0,
                "reason": "Stop after definition-focused evidence expansion.",
            }
        )

        return selected, actions, qtype

    # Result or dataset questions.
    if qtype["is_result"] or qtype["is_data"]:
        added_chunks = add_unique_units(
            selected=selected,
            candidates=ranked_all[:7],
            selected_by="ReadMoreForResultOrData",
        )

        actions.append(
            {
                "action": "ReadMoreForResultOrData",
                "added_units": added_chunks,
                "reason": "Result or data question may require experiment details.",
            }
        )

        if qtype["is_data"]:
            data_query = build_data_query(question)

            data_section_units = []

            if use_section_expansion:
                data_section_units = rank_section_aware_units(
                    question=question,
                    units=retrievable_units,
                    section_keywords=[
                        "data",
                        "dataset",
                        "datasets",
                        "corpus",
                        "corpora",
                        "experimental setup",
                        "experiments",
                        "setup",
                    ],
                    expanded_query=data_query,
                    top_k=5,
                )

            added_data_sections = add_unique_units(
                selected=selected,
                candidates=data_section_units,
                selected_by="DataSectionExpansion",
                max_new=3,
            )

            if added_data_sections > 0:
                actions.append(
                    {
                        "action": "DataSectionExpansion",
                        "added_units": added_data_sections,
                        "reason": "Dataset or language-pair question; read likely data or experimental setup sections.",
                    }
                )

        added_tables = add_unique_units(
            selected=selected,
            candidates=ranked_tables,
            selected_by="ReadTable",
            max_new=2,
        )

        if added_tables > 0:
            actions.append(
                {
                    "action": "ReadTable",
                    "added_units": added_tables,
                    "reason": "Tables are useful for numerical results, datasets or comparisons.",
                }
            )

    elif qtype["is_method"] or qtype["is_complex"]:
        added_more = add_unique_units(
            selected=selected,
            candidates=ranked_all[:7],
            selected_by="ReadMoreForMethodOrComplex",
        )

        actions.append(
            {
                "action": "ReadMoreForMethodOrComplex",
                "added_units": added_more,
                "reason": "Method or complex question may require more context.",
            }
        )

    else:
        added_default = add_unique_units(
            selected=selected,
            candidates=ranked_all[:5],
            selected_by="ReadDefaultTop5",
        )

        actions.append(
            {
                "action": "ReadDefaultTop5",
                "added_units": added_default,
                "reason": "Default reading budget.",
            }
        )

    if qtype["is_figure"]:
        added_figures = add_unique_units(
            selected=selected,
            candidates=ranked_figures,
            selected_by="ReadFigureCaption",
            max_new=2,
        )

        if added_figures > 0:
            actions.append(
                {
                    "action": "ReadFigureCaption",
                    "added_units": added_figures,
                    "reason": "Question appears to refer to a figure, diagram or architecture.",
                }
            )

    actions.append(
        {
            "action": "Stop",
            "added_units": 0,
            "reason": "Controller v3 stops after applying question-type and section-aware rules.",
        }
    )

    return selected, actions, qtype


def run_controller_v3(
    input_path: str,
    use_section_expansion: bool = True,
) -> List[Dict[str, Any]]:
    papers = read_jsonl(input_path)
    predictions = []

    for paper in tqdm(papers, desc="Running Controller v3"):
        evidence_units = paper["evidence_units"]

        for question in paper["questions"]:
            selected_units, actions, qtype = run_controller_for_question_v3(
                question=question["question"],
                evidence_units=evidence_units,
                use_section_expansion=use_section_expansion,
            )

            raw_answers = question.get("raw_answers", {})

            predictions.append(
                {
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "question_type": qtype,
                    "reference_answers": extract_reference_answers(raw_answers),
                    "gold_evidence": extract_gold_evidence(raw_answers),
                    "retrieved_units": selected_units,
                    "actions": actions,
                }
            )

    return predictions


def main():
    input_path = "data/processed/qasper_validation_50.jsonl"
    output_path = "outputs/validation50_controller_v3.jsonl"
    summary_path = "outputs/validation50_controller_v3_threshold_sweep.csv"

    predictions = run_controller_v3(input_path)
    write_jsonl(predictions, output_path)

    cost_stats = compute_cost_stats(predictions)
    summary_rows = []

    for threshold in [0.3, 0.5, 0.7]:
        eval_stats = evaluate_predictions(predictions, threshold=threshold)

        row = {
            "method": "ControllerV3",
            "threshold": threshold,
            "total_questions_with_gold": eval_stats["total_questions_with_gold"],
            "question_hit_rate": round(eval_stats["question_hit_rate"], 4),
            "evidence_recall": round(eval_stats["evidence_recall"], 4),
            "average_best_overlap": round(eval_stats["average_best_overlap"], 4),
            "avg_retrieved_units": cost_stats["avg_retrieved_units"],
            "avg_evidence_words": cost_stats["avg_evidence_words"],
            "avg_estimated_tokens": cost_stats["avg_estimated_tokens"],
            "avg_chunks": cost_stats["avg_chunks"],
            "avg_tables": cost_stats["avg_tables"],
            "avg_figures": cost_stats["avg_figures"],
            "avg_abstracts": cost_stats["avg_abstracts"],
            "avg_action_steps": cost_stats["avg_action_steps"],
        }

        summary_rows.append(row)

    write_csv(summary_rows, summary_path)

    print("\nController v3 summary:")
    for row in summary_rows:
        print(row)

    print("\nAction counts:")
    print(cost_stats["action_counts"])

    print(f"\nSaved predictions to {output_path}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
