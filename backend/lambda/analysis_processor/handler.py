"""S3-triggered completion Lambda. Fires when results/{user_id}/{analysis_id}/report.json lands.

boto3-only by design (see item 7 of the pipeline spec): no dependency on the rest of the
backend package (no services/, no core.settings, no pandas/sklearn/fastapi), so this stays
small enough to deploy without the numpy layer already vendored in this directory. Config
comes from plain Lambda environment variables, not the shared Settings class.
"""

from __future__ import annotations

import os
from urllib.parse import unquote_plus

import boto3

TABLE_NAME = os.environ.get("DDB_ANALYSES_TABLE", "retaillen-analyses")
TOPIC_ARN = os.environ.get("SNS_ANALYSIS_COMPLETE_TOPIC_ARN", "")
RESULTS_PREFIX = os.environ.get("S3_PREFIX_RESULTS", "results/")
DDB_ENDPOINT = os.environ.get("DDB_ENDPOINT", "").strip()


def _dynamodb_table():
    kwargs = {"endpoint_url": DDB_ENDPOINT} if DDB_ENDPOINT else {}
    return boto3.resource("dynamodb", **kwargs).Table(TABLE_NAME)


def _parse_result_key(key: str) -> tuple[str, str, str]:
    """results/{user_id}/{analysis_id}/report.json -> (user_id, analysis_id, filename)."""
    relative = key.removeprefix(RESULTS_PREFIX)
    user_id, analysis_id, filename = relative.split("/", 2)
    return user_id, analysis_id, filename


def handler(event: dict, _context: object = None) -> dict:
    table = _dynamodb_table()
    sns = boto3.client("sns")

    for record in event.get("Records", []):
        key = unquote_plus(record["s3"]["object"]["key"])
        user_id, analysis_id, filename = _parse_result_key(key)

        # This Lambda only reacts to the final report.json write, not metadata.json.
        if filename != "report.json":
            continue

        table.update_item(
            Key={"analysis_id": analysis_id},
            UpdateExpression="SET #status = :status, s3_result_key = :key",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "done", ":key": key},
        )

        if TOPIC_ARN:
            sns.publish(
                TopicArn=TOPIC_ARN,
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

    return {"status": "ok"}
