"""SNS: SMS OTP at sign-up; analysis-complete notifications."""

from __future__ import annotations


def publish_otp(phone: str, code: str) -> None:
    # TODO: SNS publish SMS
    _ = (phone, code)


def publish_analysis_complete(user_id: str, analysis_id: str) -> None:
    # TODO: SNS publish to analysis-complete topic
    _ = (user_id, analysis_id)
