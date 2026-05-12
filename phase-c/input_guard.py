from __future__ import annotations

import asyncio
import base64
import re
import time
from dataclasses import dataclass


VN_PII = {
    "cccd": re.compile(r"\b\d{12}\b"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)"),
    "phone_intl": re.compile(r"(?<!\d)\+1[-\s]?\d{3}[-\s]?\d{4}(?!\d)"),
    "tax_code": re.compile(r"\b\d{10}(?:-\d{3})?\b"),
    "email": re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b"),
    "street_address": re.compile(r"\b\d{1,5}\s+[A-ZÀ-Ỹ][\wÀ-ỹ.'-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ.'-]*){0,4}\s+(?:Street|St|Road|Rd|Avenue|Ave|Le Loi|Lê Lợi)\b", re.IGNORECASE),
}

INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bignore (all )?(previous|prior|system) instructions\b",
        r"\bpretend you are\b",
        r"\bfrom now on\b.*\b(ignore|no restrictions|jailbreak)\b",
        r"\bDAN\b",
        r"\bjailbreak\b",
        r"\bdeveloper mode\b",
        r"\bwithout restrictions\b",
        r"\bdecode this base64\b",
        r"\bhidden instruction\b",
    ]
]


@dataclass
class GuardResult:
    ok: bool
    text: str
    reason: str
    latency_ms: float


class InputGuard:
    def __init__(self, use_presidio: bool = True, fast_mode: bool = True):
        self.fast_mode = fast_mode
        self.analyzer = None
        self.anonymizer = None
        if use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                from presidio_anonymizer import AnonymizerEngine

                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
            except Exception as exc:
                print(f"[WARN] Presidio unavailable; regex PII guard remains active: {exc}")

    def scrub_vn(self, text: str) -> tuple[str, list[str]]:
        found = []
        output = text
        for name, pattern in VN_PII.items():
            if pattern.search(output):
                found.append(name)
                output = pattern.sub(f"[{name.upper()}]", output)
        return output, found

    def scrub_ner(self, text: str) -> tuple[str, list[str]]:
        if not self.analyzer or not self.anonymizer or not text:
            return text, []
        try:
            results = self.analyzer.analyze(text=text, language="en")
            if not results:
                return text, []
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results).text
            return anonymized, sorted({item.entity_type for item in results})
        except Exception as exc:
            return text, [f"presidio_error:{exc}"]

    def sanitize(self, text: str) -> tuple[str, float, list[str]]:
        start = time.perf_counter()
        output, regex_found = self.scrub_vn(text or "")
        ner_found: list[str] = []
        if self._should_run_ner(output, regex_found):
            output, ner_found = self.scrub_ner(output)
        latency_ms = (time.perf_counter() - start) * 1000
        return output, latency_ms, regex_found + ner_found

    async def sanitize_async(self, text: str) -> tuple[str, float, list[str]]:
        return await asyncio.to_thread(self.sanitize, text)

    def _should_run_ner(self, text: str, regex_found: list[str]) -> bool:
        if not self.analyzer or not self.anonymizer:
            return False
        if not self.fast_mode:
            return True
        if regex_found:
            return False
        if not text or len(text) > 1000:
            return False
        # Presidio is useful for English names and organizations, but it is too
        # expensive to run on every clean query in the latency budget.
        return bool(re.search(r"\b(?:I am|I'm|from|visit)\b", text, flags=re.IGNORECASE))


class InjectionDetector:
    def check(self, text: str) -> GuardResult:
        start = time.perf_counter()
        reason = ""
        ok = True
        value = text or ""
        for pattern in INJECTION_PATTERNS:
            if pattern.search(value):
                ok = False
                reason = f"Matched injection pattern: {pattern.pattern}"
                break
        if ok:
            decoded_reason = self._check_base64_payload(value)
            if decoded_reason:
                ok = False
                reason = decoded_reason
        latency_ms = (time.perf_counter() - start) * 1000
        return GuardResult(ok=ok, text=value, reason=reason or "No injection detected", latency_ms=latency_ms)

    async def check_async(self, text: str) -> GuardResult:
        return await asyncio.to_thread(self.check, text)

    def _check_base64_payload(self, text: str) -> str:
        for token in re.findall(r"[A-Za-z0-9+/=]{16,}", text):
            try:
                decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="ignore")
            except Exception:
                continue
            if any(pattern.search(decoded) for pattern in INJECTION_PATTERNS):
                return "Decoded base64 contains prompt-injection language"
        return ""


class TopicGuard:
    def __init__(self, allowed_topics: list[str] | None = None):
        self.allowed_topics = allowed_topics or [
            "bao cao tai chinh",
            "bao ve du lieu ca nhan",
            "nghi dinh 13",
            "du lieu ca nhan",
            "rag evaluation",
            "guardrails",
            "context precision",
            "context recall",
            "cohen kappa",
            "llm judge",
            "audit log",
            "latency p95",
            "công ty",
            "thuế",
        ]
        self.allowed_terms = {term for topic in self.allowed_topics for term in _terms(topic)}

    def check(self, text: str) -> tuple[bool, str]:
        query_terms = set(_terms(text or ""))
        if not query_terms:
            return False, "Cau hoi trong hoac khong co noi dung de phan loai."
        overlap = query_terms & self.allowed_terms
        if overlap:
            return True, f"On topic via terms: {', '.join(sorted(overlap)[:5])}"
        return (
            False,
            "Xin loi, toi chi ho tro cau hoi trong pham vi tai lieu cua bai lab. "
            "Hay dat cau hoi lien quan den bao cao tai chinh, du lieu ca nhan, RAG evaluation hoac guardrails.",
        )

    async def check_async(self, text: str) -> tuple[bool, str]:
        return await asyncio.to_thread(self.check, text)


def _terms(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\wÀ-ỹ]+", text, flags=re.UNICODE) if len(token) > 2]

