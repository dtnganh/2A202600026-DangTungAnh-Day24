from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .paths import DOCS_DIR


TOKEN_RE = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


@dataclass
class Chunk:
    text: str
    source: str
    index: int


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def load_markdown_documents(docs_dir: Path = DOCS_DIR) -> list[tuple[str, str]]:
    docs = []
    for path in sorted(docs_dir.glob("**/*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            docs.append((str(path.relative_to(docs_dir)), text))
    if not docs:
        raise RuntimeError(f"No markdown documents found in {docs_dir}")
    return docs


def split_text(text: str, chunk_size: int = 1200, overlap: int = 160) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
        else:
            current = ""
            step = max(1, chunk_size - overlap)
            for start in range(0, len(paragraph), step):
                part = paragraph[start : start + chunk_size].strip()
                if part:
                    chunks.append(part)
    if current:
        chunks.append(current)
    return chunks


def build_chunks(docs_dir: Path = DOCS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for source, text in load_markdown_documents(docs_dir):
        for idx, chunk in enumerate(split_text(text)):
            chunks.append(Chunk(text=chunk, source=source, index=idx))
    return chunks


def retrieve(query: str, chunks: list[Chunk], top_k: int = 5) -> list[Chunk]:
    query_terms = set(tokenize(query))
    if not query_terms:
        return chunks[:top_k]

    scored: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        terms = tokenize(chunk.text)
        term_set = set(terms)
        overlap = len(query_terms & term_set)
        phrase_bonus = sum(1 for term in query_terms if term in chunk.text.lower())
        score = overlap * 2 + phrase_bonus * 0.2
        if score:
            score += min(len(chunk.text), 1600) / 10000
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for score, chunk in scored[:top_k] if score > 0] or chunks[:top_k]


def extractive_answer(query: str, contexts: list[str]) -> str:
    if not contexts:
        return "Khong tim thay thong tin trong tai lieu."

    query_terms = set(tokenize(query))
    candidates: list[str] = []
    for context in contexts:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
            sentence = sentence.strip(" -\t")
            if sentence and len(sentence) > 30 and not sentence.startswith("#"):
                candidates.append(sentence)

    if not candidates:
        return contexts[0][:800].strip()

    def score(sentence: str) -> tuple[int, int]:
        terms = set(tokenize(sentence))
        numeric_bonus = 2 if re.search(r"\d", sentence) else 0
        return (len(query_terms & terms) + numeric_bonus, -len(sentence))

    best = max(candidates, key=score)
    return best[:1200]


class LocalRAGPipeline:
    def __init__(self, docs_dir: Path = DOCS_DIR, top_k: int = 5):
        self.docs_dir = docs_dir
        self.top_k = top_k
        self.chunks = build_chunks(docs_dir)

    def run_query(self, query: str) -> tuple[str, list[str]]:
        retrieved = retrieve(query, self.chunks, self.top_k)
        contexts = [chunk.text for chunk in retrieved]
        return extractive_answer(query, contexts), contexts

