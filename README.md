# Lab 24 — Full Evaluation & Guardrail System

## Overview
Hệ thống Evaluation và Guardrails hoàn chỉnh cho pipeline RAG, tích hợp RAGAS, LLM-as-Judge và multi-layer guardrails.

## Setup
```bash
E:\Vinuni\lab24\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
# edit .env and set OPENAI_API_KEY
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
E:\Vinuni\lab24\venv\Scripts\python.exe phase-c/output_guard.py --mode auto
E:\Vinuni\lab24\venv\Scripts\python.exe phase-c/full_pipeline.py --n 100

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
- Adversarial defense: 100.0% detection on 20 crafted attacks
- Output guard smoke test: heuristic mode only, unsafe detection 70.0%, safe false positive 0.0%, P95 latency ~0.015ms
- Full pipeline benchmark: 100 requests, current run exits at L1 for many queries; L1 P95 ~0.713ms and total P95 ~0.718ms. Need rerun with on-topic query set to measure L2/L3.

### Phase D (Blueprint)
[Link to blueprint.md](phase-d/blueprint.md)

## Lessons Learned
- RAGAS exposes weaknesses that a normal demo can hide: retrieval precision can look strong while faithfulness and answer relevancy remain weak.
- Pairwise LLM judging needs bias checks. In this run, position and length bias are visible even with swap-and-average, so the judge result should be interpreted alongside the bias report.
- Guardrails should be benchmarked layer by layer. The local input layer is fast enough, but the output guard still needs a real Llama Guard 3/Groq run before final submission.

## Notes

OpenAI-backed Phase A/B artifacts have been generated with `gpt-4o-mini`. Phase C output guard currently includes a local heuristic smoke test; final Llama Guard 3 results still need Groq or a self-hosted model.
