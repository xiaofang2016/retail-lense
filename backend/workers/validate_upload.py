"""EC2 worker: schema-check uploaded CSV/Excel after it lands in S3."""

from __future__ import annotations


def run() -> None:
    # TODO: receive SQS message, download S3 object, shared.schema.validate, update Analyses
    raise NotImplementedError


if __name__ == "__main__":
    run()
