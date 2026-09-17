"""OpenAI client. API key from Secrets Manager, not Bedrock."""

from __future__ import annotations

from typing import Any

from core.settings import get_settings
from services.secrets import get_secret

_SYSTEM_PROMPT = (
    "You are a retail analytics advisor. Given RFM segmentation results for an "
    "e-commerce store, write concise, actionable recommendations grounded only in "
    "the numbers provided. Do not invent figures that are not given to you."
)


def generate_advice(insights: dict[str, Any]) -> str:
    settings = get_settings()
    api_key = get_secret(settings.openai_secret_name)
    if not api_key:
        return ""

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Segmentation insights (JSON): {insights}"},
        ],
    )
    return response.choices[0].message.content or ""
