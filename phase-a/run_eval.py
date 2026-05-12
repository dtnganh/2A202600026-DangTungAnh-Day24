from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import parse_contexts, read_csv, write_csv, write_json
from lab24_core.env import load_env, require_env
from lab24_core.paths import PHASE_A
from lab24_core.rag_adapter import build_rag


METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def run_answers(testset_path: Path, rag_mode: str, limit: int | None) -> list[dict[str, object]]:
    rows = read_csv(testset_path)
    if limit:
        rows = rows[:limit]
    if not rows:
        raise RuntimeError(f"No rows found in {testset_path}")

    rag = build_rag(rag_mode)
    answers = []
    for idx, row in enumerate(rows, start=1):
        question = row.get("question", "").strip()
        if not question:
            continue
        print(f"[{idx}/{len(rows)}] {question[:80]}")
        answer, contexts = rag.run_query(question)
        answers.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": row.get("ground_truth", ""),
                "evolution_type": row.get("evolution_type", ""),
            }
        )
    return answers


def evaluate_with_ragas(answer_rows: list[dict[str, object]], model: str) -> list[dict[str, object]]:
    load_env()
    require_env("OPENAI_API_KEY")
    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    except ImportError as exc:
        raise RuntimeError(f"Missing dependency for RAGAS evaluation: {exc}") from exc

    dataset = Dataset.from_list(
        [
            {
                "question": row["question"],
                "answer": row["answer"],
                "contexts": parse_contexts(row["contexts"]),
                "ground_truth": row["ground_truth"],
            }
            for row in answer_rows
        ]
    )
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=ChatOpenAI(model=model, temperature=0),
        embeddings=OpenAIEmbeddings(),
    )
    scored_df = scores.to_pandas()
    scored_rows = scored_df.to_dict(orient="records")
    for scored, original in zip(scored_rows, answer_rows):
        scored.setdefault("evolution_type", original.get("evolution_type", ""))
    return scored_rows


def summarize(rows: list[dict[str, object]]) -> dict[str, float]:
    summary = {}
    for metric in METRICS:
        values = []
        for row in rows:
            try:
                values.append(float(row.get(metric, "")))
            except (TypeError, ValueError):
                pass
        if values:
            summary[metric] = statistics.fmean(values)
    return summary


def check_thresholds(summary: dict[str, float], thresholds: dict[str, float]) -> bool:
    ok = True
    for metric, threshold in thresholds.items():
        value = summary.get(metric)
        if value is None:
            print(f"[FAIL] Missing metric: {metric}")
            ok = False
        elif value < threshold:
            print(f"[FAIL] {metric}={value:.4f} < {threshold:.4f}")
            ok = False
        else:
            print(f"[OK] {metric}={value:.4f} >= {threshold:.4f}")
    return ok


def parse_thresholds(items: list[str]) -> dict[str, float]:
    thresholds = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Threshold must be metric=value, got {item}")
        key, value = item.split("=", 1)
        thresholds[key.strip()] = float(value)
    return thresholds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testset", type=Path, default=PHASE_A / "testset_v1.csv")
    parser.add_argument("--answers-output", type=Path, default=PHASE_A / "rag_answers.csv")
    parser.add_argument("--results-output", type=Path, default=PHASE_A / "ragas_results.csv")
    parser.add_argument("--summary-output", type=Path, default=PHASE_A / "ragas_summary.json")
    parser.add_argument("--rag-mode", choices=["auto", "local", "lab18"], default="auto")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--answers-only", action="store_true")
    parser.add_argument("--threshold", action="append", default=[])
    args = parser.parse_args()

    answer_rows = run_answers(args.testset, args.rag_mode, args.limit)
    write_csv(args.answers_output, answer_rows)
    print(f"[OK] Saved generated answers to {args.answers_output}")
    if args.answers_only:
        return

    scored_rows = evaluate_with_ragas(answer_rows, args.model)
    write_csv(args.results_output, scored_rows)
    summary = summarize(scored_rows)
    write_json(args.summary_output, summary)
    print(f"[OK] Saved RAGAS results to {args.results_output}")
    print(f"[OK] Saved summary to {args.summary_output}")

    thresholds = parse_thresholds(args.threshold)
    if thresholds and not check_thresholds(summary, thresholds):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

