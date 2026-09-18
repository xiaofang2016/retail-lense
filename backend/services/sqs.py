"""SQS between the S3 uploads/ notification and the EC2 clustering worker. Not Lambda.

enqueue_analysis() is implemented for completeness/testability but is not used by the
production flow: S3's bucket notification sends straight to SQS on PUT, FastAPI never
enqueues a message itself.
"""

from __future__ import annotations

import json
from typing import Any

from core.settings import get_settings


def sqs_client():
    import boto3

    settings = get_settings()
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region or "us-east-1",
        ).client("sqs")
    return boto3.client("sqs", region_name=settings.aws_region or "us-east-1")



def enqueue_analysis(message: dict[str, Any]) -> None:
    settings = get_settings()
    sqs_client().send_message(
        QueueUrl=settings.sqs_analysis_queue_url,
        MessageBody=json.dumps(message),
    )


def receive_jobs(max_messages: int = 1, wait_time_seconds: int = 10) -> list[dict[str, Any]]:
    """Long-poll for jobs. Each item is {"body": <parsed message>, "receipt_handle": str}."""
    settings = get_settings()
    print(settings.sqs_analysis_queue_url)
    response = sqs_client().receive_message(
        QueueUrl=settings.sqs_analysis_queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time_seconds,
    )
    jobs: list[dict[str, Any]] = []
    for message in response.get("Messages", []):
        jobs.append(
            {
                "body": json.loads(message["Body"]),
                "receipt_handle": message["ReceiptHandle"],
            }
        )
    return jobs


def delete_job(receipt_handle: str) -> None:
    settings = get_settings()
    sqs_client().delete_message(
        QueueUrl=settings.sqs_analysis_queue_url,
        ReceiptHandle=receipt_handle,
    )
