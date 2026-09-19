"""Analysis timestamps are UTC ISO strings in DynamoDB; show them in Auckland time."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

DISPLAY_TZ = ZoneInfo("Pacific/Auckland")


def parse_created_at(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_submitted(value: str | datetime) -> str:
    local = parse_created_at(value).astimezone(DISPLAY_TZ)
    return local.strftime("%d %b %Y, %H:%M")
