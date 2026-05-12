from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import read_csv
from lab24_core.paths import PHASE_B


def pct(num: int, den: int) -> str:
    return "0.0%" if den == 0 else f"{num / den:.1%}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=PHASE_B / "pairwise_results.csv")
    parser.add_argument("--output", type=Path, default=PHASE_B / "judge_bias_report.md")
    args = parser.parse_args()

    rows = read_csv(args.input)
    if not rows:
        raise RuntimeError(f"No rows found in {args.input}")

    total = len(rows)
    run1_a_wins = sum(1 for row in rows if str(row.get("run1_winner", "")).upper() == "A")

    longer_wins = 0
    longer_total = 0
    for row in rows:
        len_a = len(row.get("answer_a", ""))
        len_b = len(row.get("answer_b", ""))
        winner = str(row.get("winner_after_swap", "")).upper()
        if len_a == len_b or winner not in {"A", "B"}:
            continue
        longer_total += 1
        if (len_a > len_b and winner == "A") or (len_b > len_a and winner == "B"):
            longer_wins += 1

    lines = [
        "# Judge Bias Report",
        "",
        "## Quantified Bias Checks",
        "",
        "| Bias | Measurement | Result | Interpretation |",
        "|---|---:|---:|---|",
        (
            f"| Position bias | A wins when listed first | {run1_a_wins}/{total} ({pct(run1_a_wins, total)}) | "
            "Expected near 50%; values above 55% suggest first-position preference. |"
        ),
        (
            f"| Length bias | Longer answer wins | {longer_wins}/{longer_total} ({pct(longer_wins, longer_total)}) | "
            "Values above 55% suggest the judge rewards verbosity. |"
        ),
        "",
        "## Mitigation Strategy",
        "",
        "- Keep swap-and-average for all pairwise judgments.",
        "- Keep concise rubric wording that prioritizes factual accuracy over style.",
        "- Track length-bias statistics in every judge run before trusting the aggregate result.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Saved bias report to {args.output}")


if __name__ == "__main__":
    main()

