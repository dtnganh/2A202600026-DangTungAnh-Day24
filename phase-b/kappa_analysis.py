from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import read_csv, write_csv, write_json
from lab24_core.paths import PHASE_B


def interpretation(kappa: float) -> str:
    if kappa < 0:
        return "Worse than chance - judge labels are systematically misaligned."
    if kappa < 0.2:
        return "Slight agreement - not reliable."
    if kappa < 0.4:
        return "Fair agreement - still weak."
    if kappa < 0.6:
        return "Moderate agreement - usable for monitoring with caution."
    if kappa < 0.8:
        return "Substantial agreement - production-ready for this rubric."
    return "Almost perfect agreement - uncommon and strong."


def make_template(pairwise_path: Path, output_path: Path, limit: int) -> None:
    rows = read_csv(pairwise_path)[:limit]
    template = [
        {
            "question_id": row.get("question_id", idx),
            "question": row.get("question", ""),
            "answer_a": row.get("answer_a", ""),
            "answer_b": row.get("answer_b", ""),
            "human_winner": "",
            "confidence": "",
            "notes": "",
        }
        for idx, row in enumerate(rows, start=1)
    ]
    write_csv(output_path, template)
    print(f"[OK] Saved human labeling template to {output_path}")


def compute_kappa(pairwise_path: Path, human_path: Path, output_path: Path) -> None:
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError as exc:
        raise RuntimeError(f"scikit-learn is required for Cohen's kappa: {exc}") from exc

    pairwise = {str(row.get("question_id")): row for row in read_csv(pairwise_path)}
    human_rows = read_csv(human_path)
    human, judge = [], []
    for row in human_rows:
        qid = str(row.get("question_id"))
        human_winner = str(row.get("human_winner", "")).strip()
        if not human_winner:
            continue
        judge_row = pairwise.get(qid)
        if not judge_row:
            continue
        human.append(human_winner)
        judge.append(str(judge_row.get("winner_after_swap", "")).strip())
    if len(human) < 2:
        raise RuntimeError("Need at least 2 matched human labels to compute kappa.")

    kappa = float(cohen_kappa_score(human, judge))
    summary = {
        "num_labels": len(human),
        "cohen_kappa": kappa,
        "interpretation": interpretation(kappa),
        "root_cause_required": kappa < 0.6,
    }
    write_json(output_path, summary)
    print(f"Cohen's kappa: {kappa:.3f}")
    print(summary["interpretation"])
    if kappa < 0.6:
        print("[ACTION] Write a short root-cause analysis in judge_bias_report.md or README.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairwise", type=Path, default=PHASE_B / "pairwise_results.csv")
    parser.add_argument("--human", type=Path, default=PHASE_B / "human_labels.csv")
    parser.add_argument("--summary", type=Path, default=PHASE_B / "kappa_summary.json")
    parser.add_argument("--make-template", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.make_template:
        make_template(args.pairwise, args.human, args.limit)
    else:
        compute_kappa(args.pairwise, args.human, args.summary)


if __name__ == "__main__":
    main()

