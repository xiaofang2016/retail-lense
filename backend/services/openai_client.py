"""OpenAI client. API key from Secrets Manager, not Bedrock."""

from __future__ import annotations

from typing import Any

from core.settings import get_settings
from services.secrets import get_secret


# The worker processes jobs sequentially, so a hung call stalls every analysis behind it
# in the queue -- a timeout bounds the worst case instead of blocking indefinitely.
_REQUEST_TIMEOUT_SECONDS = 30.0
# The SDK already retries 429/5xx with backoff; bump past its default (2) for a call that's
# easy to silently lose to a single transient blip, given the outer try/except swallows it.
_MAX_RETRIES = 3
# Low, not zero: reduces embellishment/hallucination for "grounded, don't invent figures"
# advice while still allowing natural phrasing, rather than fully deterministic output.
_TEMPERATURE = 0.3
# Caps cost/latency for what the prompt already asks for -- concise recommendations, not
# an essay.
_MAX_COMPLETION_TOKENS = 500

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

    client = OpenAI(api_key=api_key, timeout=_REQUEST_TIMEOUT_SECONDS, max_retries=_MAX_RETRIES)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=_TEMPERATURE,
        max_tokens=_MAX_COMPLETION_TOKENS,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Segmentation insights (JSON): {insights}"},
        ],
    )
    return response.choices[0].message.content or ""
