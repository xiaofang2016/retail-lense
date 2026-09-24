"""SNS: SMS OTP for optional 2FA; analysis-complete email subscriptions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

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
    from core.aws import client as aws_client

    return aws_client("sns")


def publish_otp(phone: str, code: str) -> None:
    get_sns_sender().publish_otp(phone, code)


@dataclass
class AnalysisCompleteSubscription:
    protocol: str
    endpoint: str
    user_id: str
    arn: str


_memory_subscriptions: list[AnalysisCompleteSubscription] = []


def memory_subscriptions() -> list[AnalysisCompleteSubscription]:
    return list(_memory_subscriptions)


def reset_memory_subscriptions() -> None:
    _memory_subscriptions.clear()


def _use_aws_topic() -> bool:
    settings = get_settings()
    if settings.app_env == "test":
        return False
    return bool(settings.sns_analysis_complete_topic_arn)


def subscribe_analysis_complete_email(*, email: str, user_id: str) -> str:
    """Subscribe one address to the completion topic, filtered to this user_id."""
    endpoint = email.strip().lower()
    settings = get_settings()
    if settings.app_env == "aws" and not settings.sns_analysis_complete_topic_arn:
        raise RuntimeError("SNS_ANALYSIS_COMPLETE_TOPIC_ARN is not set")
    if _use_aws_topic():
        response = _sns_client().subscribe(
            TopicArn=get_settings().sns_analysis_complete_topic_arn,
            Protocol="email",
            Endpoint=endpoint,
            ReturnSubscriptionArn=True,
            Attributes={"FilterPolicy": json.dumps({"user_id": [user_id]})},
        )
        arn = str(response["SubscriptionArn"])
        logger.info("sns email subscribe user_id=%s arn=%s", user_id, arn)
        return arn

    arn = f"arn:aws:sns:memory:retaillen-analysis-complete:{uuid4()}"
    _memory_subscriptions.append(
        AnalysisCompleteSubscription(protocol="email", endpoint=endpoint, user_id=user_id, arn=arn)
    )
    logger.info("sns email subscribe (memory) user_id=%s endpoint=%s", user_id, endpoint)
    return arn


def unsubscribe_analysis_complete(subscription_arn: str) -> None:
    if not subscription_arn:
        return
    if ":sns:memory:" in subscription_arn or not _use_aws_topic():
        _memory_subscriptions[:] = [item for item in _memory_subscriptions if item.arn != subscription_arn]
        return
    from botocore.exceptions import ClientError

    try:
        _sns_client().unsubscribe(SubscriptionArn=subscription_arn)
    except ClientError as exc:
        code = (exc.response.get("Error") or {}).get("Code") or ""
        if code in {"NotFound", "NotFoundException"}:
            return
        raise


def publish_analysis_complete(user_id: str, analysis_id: str) -> None:
    """Not called by the real completion Lambda (backend/lambda/analysis_processor/handler.py
    is deliberately boto3-only and self-contained, with its own inline SNS publish) -- kept
    here as a reusable equivalent for anywhere else in the backend/worker that needs it."""
    settings = get_settings()
    if not settings.sns_analysis_complete_topic_arn:
        return
    _sns_client().publish(
        TopicArn=settings.sns_analysis_complete_topic_arn,
        Subject="Your Retail Lense analysis is ready",
        Message=(
            f"Analysis {analysis_id} is complete. "
            "Open Retail Lense to view the report."
        ),
        MessageAttributes={
            "user_id": {"DataType": "String", "StringValue": user_id},
            "analysis_id": {"DataType": "String", "StringValue": analysis_id},
        },
    )


@lru_cache(maxsize=1)
def get_sns_sender() -> SnsSender:
    settings = get_settings()
    if settings.app_env == "test" or not settings.sns_sms_enabled:
        return MemorySnsSender()
    return AwsSnsSender()
