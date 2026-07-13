"""
Structured logging with PII redaction.
Raw resume text, names, emails, phones are NEVER written to logs.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any, Dict

from .config import get_settings

settings = get_settings()

# Patterns to redact from any log message
_PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
]


class PIIRedactingFilter(logging.Filter):
    """Strips PII patterns from log records if LOG_PII=False."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not settings.LOG_PII:
            record.msg = self._redact(str(record.msg))
            record.args = ()
        return True

    @staticmethod
    def _redact(text: str) -> str:
        for pattern, replacement in _PII_PATTERNS:
            text = pattern.sub(replacement, text)
        return text


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(PIIRedactingFilter())
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[handler],
    )
    # Suppress noisy third-party loggers
    for noisy in ["httpx", "httpcore", "chromadb", "urllib3", "multipart"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
