from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent


REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "prompts.md",
    "phase-a/generate_testset.py",
    "phase-a/run_eval.py",
    "phase-a/failure_analysis.py",
    "phase-b/judge.py",
    "phase-b/kappa_analysis.py",
    "phase-b/bias_report.py",
    "phase-c/input_guard.py",
    "phase-c/output_guard.py",
    "phase-c/full_pipeline.py",
    "phase-d/blueprint.md",
    ".github/workflows/eval-gate.yml",
]


def check_required_files() -> list[str]:
    errors = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"Missing required file: {rel}")
    return errors


def check_python_syntax() -> list[str]:
    errors = []
    for path in ROOT.rglob("*.py"):
        if "venv" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"Syntax error in {path.relative_to(ROOT)}: {exc}")
    return errors


def check_yaml() -> list[str]:
    errors = []
    path = ROOT / ".github/workflows/eval-gate.yml"
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid YAML in {path.relative_to(ROOT)}: {exc}")
    return errors


def check_generated_files() -> list[str]:
    warnings = []
    csv_checks = [
        "phase-a/testset_v1.csv",
        "phase-a/ragas_results.csv",
        "phase-b/pairwise_results.csv",
        "phase-b/absolute_scores.csv",
        "phase-c/pii_test_results.csv",
        "phase-c/adversarial_test_results.csv",
        "phase-c/latency_benchmark.csv",
    ]
    for rel in csv_checks:
        path = ROOT / rel
        if not path.exists():
            warnings.append(f"Not generated yet: {rel}")
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            warnings.append(f"Generated CSV has no rows: {rel}")
    json_path = ROOT / "phase-a/ragas_summary.json"
    if json_path.exists():
        json.loads(json_path.read_text(encoding="utf-8"))
    else:
        warnings.append("Not generated yet: phase-a/ragas_summary.json")
    return warnings


def main() -> int:
    errors = []
    warnings = []
    errors.extend(check_required_files())
    errors.extend(check_python_syntax())
    errors.extend(check_yaml())
    warnings.extend(check_generated_files())

    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        return 1
    print("[OK] Static lab checks passed.")
    if warnings:
        print("[INFO] Some generated artifacts still need real runs before submission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

