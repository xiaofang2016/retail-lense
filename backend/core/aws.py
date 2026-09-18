"""boto3 session shared by S3/SQS/SNS/DynamoDB/Secrets Manager.

Local: AWS_PROFILE names a profile in ~/.aws.
EC2: unset or blank AWS_PROFILE, or a profile that does not exist in the
container, falls through to the instance role. boto3 treats AWS_PROFILE="" as
a real profile name and raises ProfileNotFound, so blanks are stripped.
"""

from __future__ import annotations

import os

_PROFILE_ENV = ("AWS_PROFILE", "AWS_DEFAULT_PROFILE")


def drop_blank_aws_profile() -> None:
    for key in _PROFILE_ENV:
        value = os.environ.get(key)
        if value is not None and not str(value).strip():
            os.environ.pop(key, None)


def session():
    import boto3
    from botocore.exceptions import ProfileNotFound

    drop_blank_aws_profile()
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return boto3.Session(region_name=region)

    profile = (
        (os.getenv("AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE") or "").strip()
    )
    if profile:
        try:
            sess = boto3.Session(profile_name=profile, region_name=region)
            sess.get_credentials()
            return sess
        except ProfileNotFound:
            for key in _PROFILE_ENV:
                os.environ.pop(key, None)
    return boto3.Session(region_name=region)


def client(service: str, **kwargs):
    return session().client(service, **kwargs)


def resource(service: str, **kwargs):
    return session().resource(service, **kwargs)
