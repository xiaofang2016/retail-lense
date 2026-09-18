"""Analyses persistence. Memory when APP_ENV=test or no DDB_ENDPOINT; DynamoDB otherwise.

Mirrors services/user_store.py: a Protocol plus in-memory and DynamoDB implementations,
selected by get_analysis_store(). Replaces the old dead put_analysis/get_analysis stubs
that used to live in services/dynamodb.py.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Protocol

from core.settings import get_settings
from shared.models import AnalysisItem


class AnalysisStore(Protocol):
    def create(self, item: AnalysisItem) -> AnalysisItem: ...

    def get(self, analysis_id: str) -> AnalysisItem | None: ...

    def delete(self, analysis_id: str) -> None: ...

    def list_by_user(self, user_id: str) -> list[AnalysisItem]: ...

    def update(self, analysis_id: str, **fields: object) -> AnalysisItem | None: ...

    def reset(self) -> None: ...


class MemoryAnalysisStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, AnalysisItem] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_id.clear()

    def create(self, item: AnalysisItem) -> AnalysisItem:
        with self._lock:
            self._by_id[item["analysis_id"]] = item
        return item

    def get(self, analysis_id: str) -> AnalysisItem | None:
        return self._by_id.get(analysis_id)

    def list_by_user(self, user_id: str) -> list[AnalysisItem]:
        return [item for item in self._by_id.values() if item["user_id"] == user_id]

    def update(self, analysis_id: str, **fields: object) -> AnalysisItem | None:
        with self._lock:
            item = self._by_id.get(analysis_id)
            if item is None:
                return None
            item.update(fields)  # type: ignore[typeddict-item]
            return item

    def delete(self, analysis_id: str) -> None:
        with self._lock:
            self._by_id.pop(analysis_id, None)

class DynamoAnalysisStore:
    def __init__(self) -> None:
        from services.dynamodb import dynamodb_resource

        settings = get_settings()
        self._ddb = dynamodb_resource()
        self._table = self._ddb.Table(settings.ddb_analyses_table)

    def reset(self) -> None:
        raise RuntimeError("reset() is only supported on the in-memory store")

    def create(self, item: AnalysisItem) -> AnalysisItem:
        self._table.put_item(Item=dict(item))
        return item

    def get(self, analysis_id: str) -> AnalysisItem | None:
        response = self._table.get_item(Key={"analysis_id": analysis_id})
        item = response.get("Item")
        return item if item else None  # type: ignore[return-value]

    def list_by_user(self, user_id: str) -> list[AnalysisItem]:
        response = self._table.query(
            IndexName="UserIndex",
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
        )
        return list(response.get("Items") or [])  # type: ignore[return-value]

    def update(self, analysis_id: str, **fields: object) -> AnalysisItem | None:
        if not fields:
            return self.get(analysis_id)

        # "status" is a reserved word in DynamoDB, so every attribute name is aliased.
        names = {f"#{key}": key for key in fields}
        values = {f":{key}": value for key, value in fields.items()}
        expression = "SET " + ", ".join(f"#{key} = :{key}" for key in fields)

        response = self._table.update_item(
            Key={"analysis_id": analysis_id},
            UpdateExpression=expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        attributes = response.get("Attributes")
        return attributes if attributes else None  # type: ignore[return-value]

    def delete(self, analysis_id: str) -> None:
        self._table.delete_item(Key={"analysis_id": analysis_id})

@lru_cache(maxsize=1)
def get_analysis_store() -> AnalysisStore:
    if get_settings().uses_dynamodb():
        return DynamoAnalysisStore()
    return MemoryAnalysisStore()
