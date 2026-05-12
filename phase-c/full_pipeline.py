from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from input_guard import InjectionDetector, InputGuard, TopicGuard
from output_guard import build_output_guard
from lab24_core.csv_utils import read_csv, write_csv
from lab24_core.paths import PHASE_A, PHASE_C
from lab24_core.rag_adapter import build_rag


REFUSAL = "Xin loi, toi khong the ho tro yeu cau nay trong pham vi he thong."
AUDIT_LOG = PHASE_C / "audit_log.jsonl"


class GuardedPipeline:
    def __init__(self, rag_mode: str = "auto", output_mode: str = "auto"):
        self.input_guard = InputGuard()
        self.topic_guard = TopicGuard()
        self.injection_detector = InjectionDetector()
        self.rag = build_rag(rag_mode)
        self.output_guard = build_output_guard(output_mode)

    async def run(self, user_input: str) -> tuple[str, dict[str, float], str]:
        timings: dict[str, float] = {}

        t0 = time.perf_counter()
        pii_task = asyncio.create_task(self.input_guard.sanitize_async(user_input))
        topic_task = asyncio.create_task(self.topic_guard.check_async(user_input))
        injection_task = asyncio.create_task(self.injection_detector.check_async(user_input))
        sanitized, _, _ = await pii_task
        topic_ok, topic_reason = await topic_task
        injection = await injection_task
        timings["L1"] = (time.perf_counter() - t0) * 1000
        if not injection.ok:
            await audit_log(user_input, REFUSAL, timings, injection.reason)
            return REFUSAL, timings, injection.reason
        if not topic_ok:
            await audit_log(user_input, topic_reason, timings, "topic_refusal")
            return topic_reason, timings, "topic_refusal"

        t0 = time.perf_counter()
        answer, _ = await asyncio.to_thread(self.rag.run_query, sanitized)
        timings["L2"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        safe, raw, _ = await asyncio.to_thread(self.output_guard.check, sanitized, answer)
        timings["L3"] = (time.perf_counter() - t0) * 1000
        if not safe:
            await audit_log(user_input, REFUSAL, timings, "output_guard_refusal")
            return REFUSAL, timings, f"output_guard:{raw}"

        await audit_log(user_input, answer, timings, "ok")
        return answer, timings, "ok"


async def audit_log(user_input: str, answer: str, timings: dict[str, float], status: str) -> None:
    record = {
        "query_sha256": hashlib.sha256(user_input.encode("utf-8")).hexdigest(),
        "answer_chars": len(answer),
        "status": status,
        "timings": {key: round(value, 3) for key, value in timings.items()},
    }
    line = json.dumps(record, ensure_ascii=False)
    await asyncio.to_thread(_append_audit_line, line)


def _append_audit_line(line: str) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[idx]


async def benchmark(n: int, rag_mode: str, output_mode: str, testset: Path, output: Path) -> None:
    rows = read_csv(testset) if testset.exists() else []
    queries = [row.get("question", "") for row in rows if row.get("question")]
    if not queries:
        queries = [
            "Nghi dinh 13 quy dinh gi ve du lieu ca nhan?",
            "Bao cao tai chinh co nhung chi tieu nao?",
            "RAGAS do faithfulness nhu the nao?",
            "Guardrails can chan PII ra sao?",
        ]
    while len(queries) < n:
        queries.extend(queries)
    queries = queries[:n]

    pipeline = GuardedPipeline(rag_mode=rag_mode, output_mode=output_mode)
    results = []
    for idx, query in enumerate(queries, start=1):
        print(f"[Benchmark {idx}/{len(queries)}] {query[:70]}")
        start = time.perf_counter()
        _, timings, status = await pipeline.run(query)
        total = (time.perf_counter() - start) * 1000
        results.append({"query": query, "status": status, **timings, "total": total})

    out_rows = []
    for row in results:
        out_rows.append({key: round(value, 3) if isinstance(value, float) else value for key, value in row.items()})
    write_csv(output, out_rows)

    for layer in ["L1", "L2", "L3", "total"]:
        values = [float(row[layer]) for row in results if layer in row]
        if values:
            print(
                f"{layer}: P50={statistics.median(values):.1f}ms "
                f"P95={percentile(values, 95):.1f}ms P99={percentile(values, 99):.1f}ms"
            )
    print(f"[OK] Saved latency benchmark to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--rag-mode", choices=["auto", "local", "lab18"], default="auto")
    parser.add_argument("--output-mode", choices=["auto", "groq", "heuristic"], default="auto")
    parser.add_argument("--testset", type=Path, default=PHASE_A / "testset_v1.csv")
    parser.add_argument("--output", type=Path, default=PHASE_C / "latency_benchmark.csv")
    args = parser.parse_args()
    asyncio.run(benchmark(args.n, args.rag_mode, args.output_mode, args.testset, args.output))


if __name__ == "__main__":
    main()
