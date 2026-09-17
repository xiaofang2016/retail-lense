"""Call OpenAI with pipeline metrics; the advice text is stored alongside the report.

Called from workers/clustering.py as a step in the single consolidated worker, not run standalone.
"""

from __future__ import annotations

from typing import Any

from services.openai_client import generate_advice


def generate(insights: dict[str, Any]) -> str:
    return generate_advice(insights)
