"""SQS between FastAPI upload handler and EC2 clustering workers. Not Lambda."""

from __future__ import annotations

from typing import Any


def enqueue_analysis(message: dict[str, Any]) -> None:
    # TODO: SendMessage to analysis queue
    _ = message


def receive_jobs(max_messages: int = 1) -> list[dict[str, Any]]:
    # TODO: ReceiveMessage + delete on success
    _ = max_messages
    return []
