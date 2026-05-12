from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import read_csv
from lab24_core.paths import PHASE_A


METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def assign_cluster(row: dict[str, object]) -> tuple[str, str, str]:
    scores = {metric: to_float(row.get(metric)) for metric in METRICS}
    evo = str(row.get("evolution_type", "")).lower()
    low = min(scores, key=scores.get)
    if "multi" in evo:
        return (
            "C1",
            "Multi-context retrieval gaps",
            "Increase top_k, add hybrid retrieval or reranking, and inspect cross-document chunk coverage.",
        )
    if scores["faithfulness"] < 0.5:
        return (
            "C3",
            "Answer not fully grounded in context",
            "Tighten grounded-generation prompt and cite only retrieved context spans.",
        )
    if scores["context_precision"] < 0.55:
        return (
            "C2",
            "Noisy/off-topic retrieved contexts",
            "Tune retrieval filters, add metadata constraints, and rerank before generation.",
        )
    if scores["context_recall"] < 0.55:
        return (
            "C4",
            "Missing relevant context",
            "Increase top_k, adjust chunk overlap and sizing.",
        )
    return (
        "C4",
        f"Weak {low} score",
        "Inspect the query, retrieved contexts, and ground truth; then tune the weakest pipeline stage.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=PHASE_A / "ragas_results.csv")
    parser.add_argument("--output", type=Path, default=PHASE_A / "failure_analysis.md")
    args = parser.parse_args()

    rows = read_csv(args.input)
    if not rows:
        raise RuntimeError(f"No rows found in {args.input}")

    for row in rows:
        row["avg"] = sum(to_float(row.get(metric)) for metric in METRICS) / len(METRICS)
        cluster, pattern, fix = assign_cluster(row)
        row["cluster"] = cluster
        row["cluster_pattern"] = pattern
        row["cluster_fix"] = fix

    bottom = sorted(rows, key=lambda item: item["avg"])[:10]
    clusters: dict[str, dict[str, object]] = {}
    for row in bottom:
        clusters.setdefault(
            str(row["cluster"]),
            {"pattern": row["cluster_pattern"], "fix": row["cluster_fix"], "examples": []},
        )
        q = row.get("question") or row.get("user_input", "")
        clusters[str(row["cluster"])]["examples"].append(str(q))

    lines = [
        "# Failure Cluster Analysis",
        "",
        "## Bottom 10 Questions",
        "",
        "| # | Question | Type | F | AR | CP | CR | Avg | Cluster |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(bottom, start=1):
        q = str(row.get("question") or row.get("user_input", "")).replace("|", "\\|")[:90]
        lines.append(
            f"| {idx} | {q} | {row.get('evolution_type', '')} | "
            f"{to_float(row.get('faithfulness')):.2f} | "
            f"{to_float(row.get('answer_relevancy')):.2f} | "
            f"{to_float(row.get('context_precision')):.2f} | "
            f"{to_float(row.get('context_recall')):.2f} | "
            f"{row['avg']:.2f} | {row['cluster']} |"
        )

    lines += ["", "## Clusters Identified", ""]
    for cluster_id, data in sorted(clusters.items()):
        examples = list(data["examples"])
        lines += [
            f"### Cluster {cluster_id}: {data['pattern']}",
            "",
            f"**Pattern:** {data['pattern']}",
            "",
            "**Examples:**",
        ]
        for example in examples[:3]:
            lines.append(f"- {example}")
        lines += ["", f"**Proposed fix:** {data['fix']}", ""]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Saved failure analysis to {args.output}")


if __name__ == "__main__":
    main()

