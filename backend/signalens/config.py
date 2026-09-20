"""Runtime configuration. The Jev key is read only from the process environment."""

from __future__ import annotations

import os

JEV_MODEL = "jev-1.13.0"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
RUBRIC_VERSION = "triage-2026-09-20-v3"
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ESTIMATED_INPUT_TOKENS = 12_000
MAX_PDF_PAGES = 100
MAX_REQUESTS_PER_MINUTE = 30


def api_key() -> str:
    return os.environ.get("TYPESAFE_API_KEY", "").strip()


def allowed_extension_origin() -> str:
    return os.environ.get("SIGNALENS_EXTENSION_ORIGIN", "").strip()
