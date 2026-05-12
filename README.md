# Lab 24 — Full Evaluation & Guardrail System

## Overview
Hệ thống Evaluation và Guardrails hoàn chỉnh cho pipeline RAG, tích hợp RAGAS, LLM-as-Judge và multi-layer guardrails.

## Setup
```bash
E:\Vinuni\lab24\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
# edit .env and set OPENAI_API_KEY + GROQ_API_KEY
```

Default OpenAI model for generation, RAGAS, and LLM-as-Judge scripts: `gpt-4o-mini`.

## How to Run

```bash
# Phase A
E:\Vinuni\lab24\venv\Scripts\python.exe phase-a/generate_testset.py
E:\Vinuni\lab24\venv\Scripts\python.exe phase-a/run_eval.py --model gpt-4o-mini
E:\Vinuni\lab24\venv\Scripts\python.exe phase-a/failure_analysis.py

# Phase B
E:\Vinuni\lab24\venv\Scripts\python.exe phase-b/judge.py pairwise --model gpt-4o-mini
E:\Vinuni\lab24\venv\Scripts\python.exe phase-b/judge.py absolute --model gpt-4o-mini
E:\Vinuni\lab24\venv\Scripts\python.exe phase-b/kappa_analysis.py --make-template
E:\Vinuni\lab24\venv\Scripts\python.exe phase-b/bias_report.py

# Phase C
E:\Vinuni\lab24\venv\Scripts\python.exe phase-c/run_guardrail_tests.py
E:\Vinuni\lab24\venv\Scripts\python.exe phase-c/output_guard.py --mode groq
E:\Vinuni\lab24\venv\Scripts\python.exe phase-c/full_pipeline.py --n 100 --output-mode groq --testset phase-c/benchmark_queries.csv

# Static check
E:\Vinuni\lab24\venv\Scripts\python.exe check_lab.py
```

## Results Summary

### Phase A (RAGAS)
- Test set: 51 questions (50% simple, 25% reasoning, 25% multi-context)
- Faithfulness: 0.484 | AR: 0.495 | CP: 0.863 | CR: 0.654
- Total eval cost: ~ $0.05
- Identified 3 failure clusters (see phase-a/failure_analysis.md)
- **Observation:** `faithfulness` (<0.5) và `answer_relevancy` (<0.5) đang ở mức thấp. Lý do khả năng cao là do pipeline Day 18 thiết lập lấy Chunk nhỏ nhưng prompt chưa có đủ hướng dẫn khiến suy luận của LLM để trả lời câu bị cụt lủn và không bám sát context, dẫn đến tính đúng đắn dựa trên context (faithfulness) bị rớt.

### Phase B (LLM-Judge)
- Cohen's kappa vs human: 1.00 (almost perfect agreement on the 10 labeled pairs)
- Position bias mitigated via swap-and-average
- Position bias observed: A wins first-position run 24/30 (80.0%)
- Length bias observed: longer answer wins 22/25 comparable cases (88.0%)

### Phase C (Guardrails)
- PII detection rate: 85.7%, P95 latency ~0.164ms
- Topic validator: 80.0% accuracy, 70.0% refuse rate
- Adversarial defense: 100.0% detection on 20 crafted attacks, 0.0% false positive on 10 legitimate queries
- Output guard via Groq safety fallback (`openai/gpt-oss-safeguard-20b`): unsafe detection 100.0%, safe false positive 0.0%, standalone P95 latency ~1870.879ms
- Full pipeline benchmark: 100 requests over `phase-c/benchmark_queries.csv`; L1 P95 ~0.644ms, L2 P95 ~10.307ms, L3 P95 ~683.851ms, total P95 ~693.010ms.
- Baseline with local heuristic output guard: total P95 ~12.8ms in `phase-c/latency_baseline.csv`; Groq safety fallback adds roughly +680ms P95 overhead.
- L3 target <100ms is not met because the currently available Groq safety model is an external API call; this is documented as the main latency bottleneck.

### Phase D (Blueprint)
[Link to blueprint.md](phase-d/blueprint.md)

## Lessons Learned
- RAGAS exposes weaknesses that a normal demo can hide: retrieval precision can look strong while faithfulness and answer relevancy remain weak.
- Pairwise LLM judging needs bias checks. In this run, position and length bias are visible even with swap-and-average, so the judge result should be interpreted alongside the bias report.
- Guardrails should be benchmarked layer by layer. The local input layer is fast enough, while API-based output safety is the main latency bottleneck.

## Notes

OpenAI-backed Phase A/B artifacts have been generated with `gpt-4o-mini`. Groq returned `model_decommissioned` for `llama-guard-3-8b` and `meta-llama/llama-guard-4-12b`, so Phase C uses the currently available Groq safety model `openai/gpt-oss-safeguard-20b` and documents that deviation.
