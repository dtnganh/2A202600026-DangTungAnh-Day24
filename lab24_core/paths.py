from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PHASE_A = ROOT / "phase-a"
PHASE_B = ROOT / "phase-b"
PHASE_C = ROOT / "phase-c"
PHASE_D = ROOT / "phase-d"

DEFAULT_LAB18_REPO = Path(r"E:\Vinuni\lab18\2A202600026-DangTungAnh-Day18")
LAB18_REPO = Path(os.getenv("LAB18_REPO", str(DEFAULT_LAB18_REPO)))


def ensure_dirs() -> None:
    for path in [DOCS_DIR, PHASE_A, PHASE_B, PHASE_C, PHASE_D, ROOT / "demo"]:
        path.mkdir(parents=True, exist_ok=True)

