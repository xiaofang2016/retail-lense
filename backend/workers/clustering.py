"""EC2 worker: RFM + K-Means on a validated upload. Long-running process on the instance."""

from __future__ import annotations


def run() -> None:
    # TODO: poll SQS (or chain after validate_upload), call ml pipeline, write S3 + DynamoDB, SNS notify
    raise NotImplementedError


if __name__ == "__main__":
    run()
