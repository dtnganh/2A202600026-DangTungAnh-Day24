from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Protocol

from .env import load_env
from .paths import DOCS_DIR, LAB18_REPO
from .simple_rag import LocalRAGPipeline


class RAGPipeline(Protocol):
    def run_query(self, query: str) -> tuple[str, list[str]]:
        ...


class Lab18Pipeline:
    def __init__(self, repo: Path = LAB18_REPO):
        if not repo.exists():
            raise RuntimeError(f"Lab 18 repo not found: {repo}")
        self.repo = repo
        sys.path.insert(0, str(repo))
        try:
            from src.pipeline import build_pipeline, run_query
        except Exception as exc:
            raise RuntimeError(f"Cannot import Lab 18 pipeline from {repo}: {exc}") from exc

        self._run_query = run_query
        self.search, self.reranker = build_pipeline()

    def run_query(self, query: str) -> tuple[str, list[str]]:
        return self._run_query(query, self.search, self.reranker)


def build_rag(mode: str = "auto") -> RAGPipeline:
    load_env()
    normalized = mode.lower()
    if normalized == "local":
        return LocalRAGPipeline(DOCS_DIR)
    if normalized == "lab18":
        return Lab18Pipeline()
    if normalized != "auto":
        raise ValueError("mode must be one of: auto, local, lab18")

    if LAB18_REPO.exists() and os.getenv("OPENAI_API_KEY"):
        try:
            return Lab18Pipeline()
        except Exception as exc:
            print(f"[WARN] Lab18 pipeline unavailable, falling back to local retriever: {exc}")
    return LocalRAGPipeline(DOCS_DIR)

