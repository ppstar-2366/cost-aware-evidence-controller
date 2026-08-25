from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi
from tqdm import tqdm

from common import (
    estimate_tokens_from_words,
    extract_gold_evidence,
    extract_reference_answers,
    read_jsonl,
    tokenize,
)


RETRIEVABLE_TYPES = {
    "abstract",
    "chunk",
    "table",
    "figure_caption",
    "figure_table",
}


def get_retrievable_units(evidence_units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        unit
        for unit in evidence_units
        if unit.get("unit_type") in RETRIEVABLE_TYPES
        and unit.get("text", "").strip()
    ]


def _prediction_unit(unit: Dict[str, Any], rank: int, score: float) -> Dict[str, Any]:
    return {
        "rank": rank,
        "score": float(score),
        "unit_id": unit["unit_id"],
        "unit_type": unit["unit_type"],
        "section_name": unit["section_name"],
        "text": unit["text"],
        "word_count": unit.get("word_count", len(unit["text"].split())),
    }


def build_bm25_index(evidence_units: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[BM25Okapi]]:
    retrievable_units = get_retrievable_units(evidence_units)
    corpus_tokens = [tokenize(unit["text"]) for unit in retrievable_units]

    if not corpus_tokens:
        return retrievable_units, None

    return retrievable_units, BM25Okapi(corpus_tokens)


def retrieve_top_k(
    question: str,
    retrievable_units: List[Dict[str, Any]],
    bm25: Optional[BM25Okapi],
    top_k: int,
) -> List[Dict[str, Any]]:
    if bm25 is None:
        return []

    query_tokens = tokenize(question)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    return [
        _prediction_unit(retrievable_units[idx], rank, float(scores[idx]))
        for rank, idx in enumerate(ranked_indices[:top_k], start=1)
    ]


def rank_units(question: str, units: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    if not units:
        return []

    corpus_tokens = [tokenize(unit["text"]) for unit in units]
    query_tokens = tokenize(question)

    if not query_tokens:
        return []

    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    return [
        _prediction_unit(units[idx], rank, float(scores[idx]))
        for rank, idx in enumerate(ranked_indices[:top_k], start=1)
    ]


def run_bm25(input_path: str, top_k: int) -> List[Dict[str, Any]]:
    papers = read_jsonl(input_path)
    predictions: List[Dict[str, Any]] = []

    for paper in tqdm(papers, desc=f"BM25 top-{top_k}"):
        retrievable_units, bm25 = build_bm25_index(paper["evidence_units"])

        for question in paper["questions"]:
            raw_answers = question.get("raw_answers", {})
            predictions.append(
                {
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "reference_answers": extract_reference_answers(raw_answers),
                    "gold_evidence": extract_gold_evidence(raw_answers),
                    "retrieved_units": retrieve_top_k(
                        question=question["question"],
                        retrievable_units=retrievable_units,
                        bm25=bm25,
                        top_k=top_k,
                    ),
                }
            )

    return predictions


def token_set(text: str) -> set:
    return set(tokenize(text))


def overlap_score(gold_text: str, predicted_text: str) -> float:
    gold_tokens = token_set(gold_text)
    predicted_tokens = token_set(predicted_text)

    if not gold_tokens:
        return 0.0

    return len(gold_tokens.intersection(predicted_tokens)) / len(gold_tokens)


def best_overlap_for_gold(gold_text: str, retrieved_units: List[Dict[str, Any]]) -> float:
    best_score = 0.0

    for unit in retrieved_units:
        best_score = max(best_score, overlap_score(gold_text, unit.get("text", "")))

    return best_score


def evaluate_predictions(
    predictions: List[Dict[str, Any]],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    total_gold_spans = 0
    covered_gold_spans = 0
    total_questions_with_gold = 0
    questions_with_hit = 0
    all_best_scores: List[float] = []

    for item in predictions:
        gold_evidence = item.get("gold_evidence", [])
        retrieved_units = item.get("retrieved_units", [])

        if not gold_evidence:
            continue

        total_questions_with_gold += 1
        question_has_hit = False

        for gold in gold_evidence:
            best_score = best_overlap_for_gold(gold, retrieved_units)
            all_best_scores.append(best_score)
            total_gold_spans += 1

            if best_score >= threshold:
                covered_gold_spans += 1
                question_has_hit = True

        if question_has_hit:
            questions_with_hit += 1

    return {
        "threshold": threshold,
        "total_questions_with_gold": total_questions_with_gold,
        "questions_with_hit": questions_with_hit,
        "question_hit_rate": questions_with_hit / total_questions_with_gold if total_questions_with_gold else 0.0,
        "total_gold_spans": total_gold_spans,
        "covered_gold_spans": covered_gold_spans,
        "evidence_recall": covered_gold_spans / total_gold_spans if total_gold_spans else 0.0,
        "average_best_overlap": sum(all_best_scores) / len(all_best_scores) if all_best_scores else 0.0,
    }


def compute_cost_stats(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_questions = len(predictions)
    total_units = 0
    total_words = 0
    unit_type_counter: Counter = Counter()
    action_counter: Counter = Counter()
    total_action_steps = 0

    for item in predictions:
        retrieved_units = item.get("retrieved_units", [])
        actions = item.get("actions", [])

        total_units += len(retrieved_units)
        total_action_steps += len(actions)

        for action in actions:
            action_counter[action.get("action", "")] += 1

        for unit in retrieved_units:
            unit_type = unit.get("unit_type", "")
            unit_type_counter[unit_type] += 1
            total_words += unit.get("word_count", len(unit.get("text", "").split()))

    avg_words = total_words / total_questions if total_questions else 0.0

    return {
        "avg_retrieved_units": round(total_units / total_questions, 2) if total_questions else 0,
        "avg_evidence_words": round(avg_words, 2),
        "avg_estimated_tokens": estimate_tokens_from_words(avg_words),
        "avg_chunks": round(unit_type_counter["chunk"] / total_questions, 2) if total_questions else 0,
        "avg_tables": round(unit_type_counter["table"] / total_questions, 2) if total_questions else 0,
        "avg_figures": round(unit_type_counter["figure_caption"] / total_questions, 2) if total_questions else 0,
        "avg_abstracts": round(unit_type_counter["abstract"] / total_questions, 2) if total_questions else 0,
        "avg_action_steps": round(total_action_steps / total_questions, 2) if total_questions else 0,
        "action_counts": dict(action_counter),
    }


def classify_question(question: str) -> Dict[str, bool]:
    q = question.lower()
    tokens = tokenize(q)

    result_words = {
        "result", "results", "performance", "accuracy", "score", "scores",
        "evaluation", "evaluate", "improvement", "improvements",
        "baseline", "baselines", "compare", "comparison", "f1", "bleu", "rouge",
    }
    data_words = {
        "dataset", "datasets", "data", "corpus", "examples", "size",
        "large", "larger", "how", "big",
    }
    method_words = {
        "how", "method", "approach", "model", "learn", "learning",
        "train", "training", "use", "used", "using", "relation",
        "relations", "propagate", "supervision", "supervised",
    }
    figure_words = {"figure", "fig", "architecture", "pipeline", "diagram", "overview"}

    is_result = any(word in tokens for word in result_words)
    is_data = any(word in tokens for word in data_words) and (
        "data" in tokens or "dataset" in tokens or "datasets" in tokens or "corpus" in tokens
    )
    is_method = any(word in tokens for word in method_words)
    is_figure = any(word in tokens for word in figure_words)
    is_definition = (
        q.startswith("what is")
        or q.startswith("what are")
        or q.startswith("what was")
    ) and len(tokens) <= 9 and not is_result
    is_complex = len(tokens) >= 12 or q.startswith("how") or q.startswith("why")

    return {
        "is_result": is_result,
        "is_data": is_data,
        "is_method": is_method,
        "is_figure": is_figure,
        "is_definition": is_definition,
        "is_complex": is_complex,
    }


def add_unique_units(
    selected: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    selected_by: str,
    max_new: Optional[int] = None,
) -> int:
    existing_ids = {unit["unit_id"] for unit in selected}
    added = 0

    for unit in candidates:
        if unit["unit_id"] in existing_ids:
            continue

        selected_unit = dict(unit)
        selected_unit["selected_by"] = selected_by
        selected.append(selected_unit)
        existing_ids.add(unit["unit_id"])
        added += 1

        if max_new is not None and added >= max_new:
            break

    return added
