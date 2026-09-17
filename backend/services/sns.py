"""SNS: SMS OTP for optional 2FA; analysis-complete notifications."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol
import json

from core.settings import get_settings

logger = logging.getLogger("sns")


@dataclass
class OutgoingSms:
    phone: str
    code: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SnsSender(Protocol):
    def publish_otp(self, phone: str, code: str) -> None: ...


class MemorySnsSender:
    def __init__(self) -> None:
        self.outbox: list[OutgoingSms] = []

    def publish_otp(self, phone: str, code: str) -> None:
        self.outbox.append(OutgoingSms(phone=phone, code=code))
        logger.info("otp sms to %s code=%s (memory sender)", phone, code)

    def clear(self) -> None:
        self.outbox.clear()


class AwsSnsSender:
    def publish_otp(self, phone: str, code: str) -> None:
        client = _sns_client()
        client.publish(
            PhoneNumber=phone,
            Message=f"Retail Lense code: {code}. Expires in 5 minutes.",
            MessageAttributes={
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                }
            },
        )
        logger.info("otp sms to %s code=%s (aws sns sender)", phone, code)


def _sns_client():
    import boto3

    settings = get_settings()
    kwargs: dict[str, str] = {"region_name": settings.aws_region}
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return boto3.client("sns", **kwargs)
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        ).client("sns")
    return boto3.client("sns", region_name=settings.aws_region)


def publish_otp(phone: str, code: str) -> None:
    get_sns_sender().publish_otp(phone, code)


def publish_analysis_complete(user_id: str, analysis_id: str) -> None:
    """Not called by the real completion Lambda (backend/lambda/analysis_processor/handler.py
    is deliberately boto3-only and self-contained, with its own inline SNS publish) -- kept
    here as a reusable equivalent for anywhere else in the backend/worker that needs it."""
    settings = get_settings()
    if not settings.sns_analysis_complete_topic_arn:
        return
    _sns_client().publish(
        TopicArn=settings.sns_analysis_complete_topic_arn,
        Message=json.dumps({"user_id": user_id, "analysis_id": analysis_id}),
        Subject="Analysis complete",
    )


@lru_cache(maxsize=1)
def get_sns_sender() -> SnsSender:
    settings = get_settings()
    if settings.app_env == "test" or not settings.sns_sms_enabled:
        return MemorySnsSender()
    return AwsSnsSender()
