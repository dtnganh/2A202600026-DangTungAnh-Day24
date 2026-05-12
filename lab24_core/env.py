from __future__ import annotations

import os
from pathlib import Path

from .paths import LAB18_REPO, ROOT


def load_env() -> None:
    """Load local .env when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        load_dotenv(LAB18_REPO / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_path_exists(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and Path(value).exists())
