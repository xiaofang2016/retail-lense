"""OpenAI client. API key from Secrets Manager, not Bedrock."""

from __future__ import annotations

from typing import Any


def generate_advice(insights: dict[str, Any]) -> str:
    # TODO: chat completion over RFM/segment summaries
    _ = insights
    return ""
