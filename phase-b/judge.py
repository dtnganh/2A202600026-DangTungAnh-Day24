from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import parse_contexts, read_csv, write_csv
from lab24_core.llm_utils import openai_chat, parse_json_object
from lab24_core.paths import PHASE_A, PHASE_B
from lab24_core.simple_rag import extractive_answer


PAIRWISE_PROMPT = """You are an impartial evaluator. Compare two answers to the same question.

Question: {question}
Answer A: {answer_a}
Answer B: {answer_b}

Rate based on:
- Factual accuracy
- Relevance to the question
- Conciseness

Output JSON only:
{{"winner": "A" or "B" or "tie", "reason": "..."}}
"""

ABSOLUTE_PROMPT = """Score the answer on 4 dimensions, each 1-5 scale:

1. Factual accuracy (1=many errors, 5=fully accurate)
2. Relevance (1=off-topic, 5=directly answers)
3. Conciseness (1=verbose, 5=appropriately brief)
4. Helpfulness (1=unclear, 5=actionable)

Question: {question}
Answer: {answer}

Output JSON only:
{{"accuracy": int, "relevance": int, "conciseness": int, "helpfulness": int, "overall": float}}
"""


def normalize_winner(value: object) -> str:
    text = str(value or "").strip().upper()
    if text in {"A", "B"}:
        return text
    return "tie"


def parse_judge_output(text: str) -> dict[str, object]:
    parsed = parse_json_object(text)
    winner = normalize_winner(parsed.get("winner"))
    return {"winner": winner, "reason": str(parsed.get("reason", "") or "No reason returned")}


def pairwise_judge_with_swap(question: str, ans1: str, ans2: str, model: str) -> dict[str, str]:
    prompt = PAIRWISE_PROMPT.format(question=question, answer_a=ans1, answer_b=ans2)
    run1 = parse_judge_output(openai_chat(prompt, model=model))

    prompt = PAIRWISE_PROMPT.format(question=question, answer_a=ans2, answer_b=ans1)
    run2_raw = parse_judge_output(openai_chat(prompt, model=model))
    run2 = dict(run2_raw)
    if run2["winner"] == "A":
        run2["winner"] = "B"
    elif run2["winner"] == "B":
        run2["winner"] = "A"

    final = run1["winner"] if run1["winner"] == run2["winner"] else "tie"
    return {
        "winner_after_swap": str(final),
        "run1_winner": str(run1["winner"]),
        "run2_winner": str(run2["winner"]),
        "run1_reason": str(run1["reason"]),
        "run2_reason": str(run2_raw["reason"]),
    }


def absolute_score(question: str, answer: str, model: str) -> dict[str, object]:
    raw = openai_chat(ABSOLUTE_PROMPT.format(question=question, answer=answer), model=model)
    parsed = parse_json_object(raw)
    dims = {}
    for key in ["accuracy", "relevance", "conciseness", "helpfulness"]:
        try:
            score = int(parsed.get(key, 0))
        except (TypeError, ValueError):
            score = 0
        dims[key] = max(1, min(5, score)) if score else 0
    valid = [value for value in dims.values() if value]
    overall = sum(valid) / len(valid) if valid else 0.0
    dims["overall"] = round(overall, 3)
    return dims


def build_answer_b(row: dict[str, str]) -> str:
    if row.get("answer_b"):
        return row["answer_b"]
    contexts = parse_contexts(row.get("contexts", ""))
    return extractive_answer(row.get("question", ""), contexts)


def run_pairwise(input_path: Path, output_path: Path, model: str, limit: int) -> None:
    rows = read_csv(input_path)[:limit]
    if len(rows) < limit:
        raise RuntimeError(f"Need at least {limit} rows in {input_path}; found {len(rows)}")
    output = []
    for idx, row in enumerate(rows, start=1):
        question = row.get("question", "")
        answer_a = row.get("answer", "") or row.get("answer_a", "")
        answer_b = build_answer_b(row)
        print(f"[Pairwise {idx}/{len(rows)}] {question[:70]}")
        judged = pairwise_judge_with_swap(question, answer_a, answer_b, model)
        output.append(
            {
                "question_id": idx,
                "question": question,
                "answer_a": answer_a,
                "answer_b": answer_b,
                **judged,
            }
        )
    write_csv(output_path, output)
    print(f"[OK] Saved pairwise results to {output_path}")


def run_absolute(input_path: Path, output_path: Path, model: str, limit: int) -> None:
    rows = read_csv(input_path)[:limit]
    if len(rows) < limit:
        raise RuntimeError(f"Need at least {limit} rows in {input_path}; found {len(rows)}")
    output = []
    for idx, row in enumerate(rows, start=1):
        question = row.get("question", "")
        answer = row.get("answer", "") or row.get("answer_a", "")
        print(f"[Absolute {idx}/{len(rows)}] {question[:70]}")
        scores = absolute_score(question, answer, model)
        output.append({"question_id": idx, "question": question, "answer": answer, **scores})
    write_csv(output_path, output)
    print(f"[OK] Saved absolute scores to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["pairwise", "absolute"])
    parser.add_argument("--input", type=Path, default=PHASE_A / "rag_answers.csv")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.mode == "pairwise":
        run_pairwise(args.input, args.output or PHASE_B / "pairwise_results.csv", args.model, args.limit)
    else:
        run_absolute(args.input, args.output or PHASE_B / "absolute_scores.csv", args.model, args.limit)


if __name__ == "__main__":
    main()

