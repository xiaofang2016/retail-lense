#!/usr/bin/env python3
"""Promote or revoke admin on a DynamoDB user.

Looks up EmailIndex or UsernameIndex, then SET is_admin.

    python infra/scripts/promote_admin.py --username anna --yes
    python infra/scripts/promote_admin.py --email anna@example.com --yes
    python infra/scripts/promote_admin.py --username anna --revoke --yes
    python infra/scripts/promote_admin.py --username anna --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, ProfileNotFound
from boto3.dynamodb.conditions import Key

ROOT = Path(__file__).resolve().parents[2]


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


def table():
    region = os.getenv("AWS_REGION", "us-east-1")
    endpoint = os.getenv("DDB_ENDPOINT", "").strip()
    profile = os.getenv("AWS_PROFILE", "").strip()
    name = os.getenv("DDB_USERS_TABLE", "retaillen-users")

    if endpoint:
        resource = boto3.resource(
            "dynamodb",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or "local",
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or "local",
        )
        return resource.Table(name)

    kwargs: dict[str, str] = {"region_name": region}
    session_kwargs = dict(kwargs)
    if profile:
        session_kwargs["profile_name"] = profile

    try:
        session = boto3.Session(**session_kwargs)
    except ProfileNotFound:
        print(
            f"warning: AWS profile '{profile}' not found; falling back to default credentials",
            file=sys.stderr,
        )
        session = boto3.Session(**kwargs)

    return session.resource("dynamodb").Table(name)


def find_user(users, email: str | None, username: str | None) -> dict | None:
    if email:
        response = users.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(email.lower()),
            Limit=1,
        )
    else:
        response = users.query(
            IndexName="UsernameIndex",
            KeyConditionExpression=Key("username").eq(username.lower()),
            Limit=1,
        )
    items = response.get("Items") or []
    return items[0] if items else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email")
    parser.add_argument("--username")
    parser.add_argument("--revoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="skip the interactive confirm")
    args = parser.parse_args()

    if bool(args.email) == bool(args.username):
        print("specify exactly one of --email or --username", file=sys.stderr)
        return 2

    load_dotenv(ROOT / ".env")
    users = table()
    item = find_user(users, args.email, args.username)
    if not item:
        who = args.email or args.username
        print(f"user not found: {who}", file=sys.stderr)
        return 1

    flag = not args.revoke
    print(f"user_id:  {item['user_id']}")
    print(f"email:    {item.get('email')}")
    print(f"username: {item.get('username')}")
    print(f"is_admin: {bool(item.get('is_admin'))} -> {flag}")

    if args.dry_run:
        print("dry-run: no changes")
        return 0

    if not args.yes:
        action = "revoke admin from" if args.revoke else "promote"
        answer = input(f"{action} this user? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("aborted")
            return 1

    users.update_item(
        Key={"user_id": item["user_id"]},
        UpdateExpression="SET is_admin = :flag",
        ExpressionAttributeValues={":flag": flag},
    )
    print("updated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(f"aws error: {exc}", file=sys.stderr)
        raise SystemExit(1)