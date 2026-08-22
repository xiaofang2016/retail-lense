#!/usr/bin/env python3
"""Create Retail Lense DynamoDB tables.

Safe to re-run: existing tables are left unchanged. Uses on-demand billing.

With DDB_ENDPOINT set (DynamoDB Local), no AWS account is required.
Without it, uses the current AWS credentials (laptop profile or EC2 instance role).

    python infra/scripts/create_dynamodb_tables.py --yes
    python infra/scripts/create_dynamodb_tables.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
ON_DEMAND = {"BillingMode": "PAY_PER_REQUEST"}


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def table_names() -> dict[str, str]:
    return {
        "users": os.getenv("DDB_USERS_TABLE", "retaillen-users"),
        "login_history": os.getenv("DDB_LOGIN_HISTORY_TABLE", "retaillen-login-history"),
        "password_reset": os.getenv("DDB_PASSWORD_RESET_TABLE", "retaillen-password-reset"),
        "otps": os.getenv("DDB_OTPS_TABLE", "retaillen-otps"),
        "analyses": os.getenv("DDB_ANALYSES_TABLE", "retaillen-analyses"),
    }


def specs(names: dict[str, str]) -> list[dict]:
    """Table definitions matching backend/services/user_store.py."""
    return [
        {
            "name": names["users"],
            "params": {
                "TableName": names["users"],
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "email", "AttributeType": "S"},
                    {"AttributeName": "username", "AttributeType": "S"},
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "EmailIndex",
                        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "UsernameIndex",
                        "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                **ON_DEMAND,
            },
        },
        {
            "name": names["login_history"],
            "params": {
                "TableName": names["login_history"],
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": "ip", "AttributeType": "S"},
                    {"AttributeName": "created_at", "AttributeType": "S"},
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "IpIndex",
                        "KeySchema": [
                            {"AttributeName": "ip", "KeyType": "HASH"},
                            {"AttributeName": "created_at", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                **ON_DEMAND,
            },
        },
        {
            "name": names["password_reset"],
            "ttl": "ttl",
            "params": {
                "TableName": names["password_reset"],
                "KeySchema": [{"AttributeName": "token", "KeyType": "HASH"}],
                "AttributeDefinitions": [{"AttributeName": "token", "AttributeType": "S"}],
                **ON_DEMAND,
            },
        },
        {
            "name": names["otps"],
            "ttl": "ttl",
            "params": {
                "TableName": names["otps"],
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "AttributeDefinitions": [{"AttributeName": "email", "AttributeType": "S"}],
                **ON_DEMAND,
            },
        },
        {
            "name": names["analyses"],
            "params": {
                "TableName": names["analyses"],
                "KeySchema": [{"AttributeName": "analysis_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "analysis_id", "AttributeType": "S"},
                    {"AttributeName": "user_id", "AttributeType": "S"},
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "UserIndex",
                        "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                **ON_DEMAND,
            },
        },
    ]


def table_exists(client, name: str) -> bool:
    try:
        client.describe_table(TableName=name)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def wait_active(client, name: str, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.describe_table(TableName=name)["Table"]["TableStatus"]
        if status == "ACTIVE":
            return
        time.sleep(3)
    raise TimeoutError(f"table {name} did not become ACTIVE")


def enable_ttl(client, name: str, attribute: str) -> None:
    try:
        client.update_time_to_live(
            TableName=name,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": attribute},
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        # Already on, or still enabling from a previous run.
        if code in {"ValidationException", "ResourceInUseException"}:
            print(f"  ttl {name}.{attribute}: skipped ({code})")
            return
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE", ""))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="skip the interactive confirm")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    names = table_names()
    region = args.region or os.getenv("AWS_REGION", "us-east-1")
    endpoint = os.getenv("DDB_ENDPOINT", "").strip()

    print(f"region:  {region}")
    if endpoint:
        print(f"endpoint: {endpoint}")
    if args.profile:
        print(f"profile: {args.profile}")
    print("tables:")
    for key, name in names.items():
        print(f"  - {key}: {name}")

    if args.dry_run:
        print("dry-run: no changes")
        return 0

    if not args.yes:
        target = "this DynamoDB endpoint" if endpoint else "this AWS account"
        answer = input(f"Create missing tables on {target}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("aborted")
            return 1

    if endpoint:
        client = boto3.client(
            "dynamodb",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or "local",
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or "local",
        )
    else:
        session_kwargs: dict[str, str] = {"region_name": region}
        if args.profile:
            session_kwargs["profile_name"] = args.profile
        client = boto3.Session(**session_kwargs).client("dynamodb")
    for spec in specs(names):
        name = spec["name"]
        if table_exists(client, name):
            print(f"exists: {name}")
        else:
            client.create_table(**spec["params"])
            print(f"creating: {name}")
            wait_active(client, name)
            print(f"active: {name}")
        if spec.get("ttl"):
            enable_ttl(client, name, spec["ttl"])
            print(f"  ttl enabled: {name}.{spec['ttl']}")

    print("done")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(f"aws error: {exc}", file=sys.stderr)
        raise SystemExit(1)
