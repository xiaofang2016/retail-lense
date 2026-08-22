"""EC2 worker: call OpenAI with pipeline metrics; store advice next to the report."""

from __future__ import annotations


def run() -> None:
    # TODO: load insights, retrieve OpenAI key from Secrets Manager, put advice on Analyses item / S3
    raise NotImplementedError


if __name__ == "__main__":
    run()
