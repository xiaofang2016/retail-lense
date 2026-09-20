"""Opt-in email subscriptions for analysis-complete SNS notifications."""

from __future__ import annotations

import logging

from schema.user import UserRecord
from services.sns import subscribe_analysis_complete_email, unsubscribe_analysis_complete
from services.user_store import UserStore, get_user_store

logger = logging.getLogger("analysis_notifications")


class AnalysisNotificationError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def set_email_notifications(user: UserRecord, enabled: bool, store: UserStore | None = None) -> UserRecord:
    users = store or get_user_store()
    fresh = users.get_by_id(user.user_id) or user

    if enabled:
        if not fresh.sns_email_subscription_arn:
            try:
                fresh.sns_email_subscription_arn = subscribe_analysis_complete_email(
                    email=fresh.email,
                    user_id=fresh.user_id,
                )
            except AnalysisNotificationError:
                raise
            except Exception as exc:
                logger.exception("sns email subscribe failed for user_id=%s", fresh.user_id)
                raise AnalysisNotificationError("Could not subscribe the account email", 502) from exc
        fresh.notify_email = True
        return users.update(fresh)

    if fresh.sns_email_subscription_arn:
        try:
            unsubscribe_analysis_complete(fresh.sns_email_subscription_arn)
        except Exception as exc:
            logger.exception("sns email unsubscribe failed for user_id=%s", fresh.user_id)
            raise AnalysisNotificationError("Could not unsubscribe the account email", 502) from exc
    fresh.sns_email_subscription_arn = ""
    fresh.notify_email = False
    return users.update(fresh)
