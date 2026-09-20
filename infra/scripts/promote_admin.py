#!/usr/bin/env python3
"""Promote or revoke admin on a DynamoDB user.

Run this on the backend EC2. That instance profile
(`retaillen-backend-runtime`) is attached to the box; boto3 picks it up from
IMDS. There is no ~/.aws on that host and AWS_PROFILE must not be set.

Frontend Streamlit EC2 only has `retaillen-frontend-runtime` (Secrets Manager),
not DynamoDB — do not run this there.

Laptop: AWS_PROFILE names a profile in ~/.aws.

    python infra/scripts/promote_admin.py --username anna --yes
    python infra/scripts/promote_admin.py --email anna@example.com --yes
    python infra/scripts/promote_admin.py --username anna --revoke --yes
    python infra/scripts/promote_admin.py --username anna --dry-run

Needs boto3 (backend/.venv on the EC2 host, or the backend image). Redis is
optional: Streamlit refreshes is_admin from GET /users/me.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION_KEY_PREFIX = "retaillen:session:"
IN_CONTAINER_ENV = "PROMOTE_ADMIN_IN_CONTAINER"


def _ensure_backend_path() -> None:
    backend = ROOT / "backend"
    if backend.is_dir():
        sys.path.insert(0, str(backend))
    elif Path("/app/core/aws.py").is_file():
        sys.path.insert(0, "/app")


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


def _in_backend_container() -> bool:
    return os.getenv(IN_CONTAINER_ENV) == "1" or Path("/.dockerenv").is_file()


def _running_compose_services() -> set[str]:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _has_aws_credentials() -> bool:
    if os.getenv("DDB_ENDPOINT", "").strip():
        return True
    if os.getenv("AWS_ACCESS_KEY_ID", "").strip():
        return True
    # Named AWS_PROFILE in .env is not credentials. On EC2 the instance role
    # comes from IMDS, not ~/.aws. Probe the same chain as backend/core/aws.py.
    os.environ.setdefault("AWS_METADATA_SERVICE_TIMEOUT", "2")
    os.environ.setdefault("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "2")
    _ensure_backend_path()
    try:
        from core.aws import session as aws_session

        return aws_session().get_credentials() is not None
    except ImportError:
        try:
            import boto3
        except ImportError:
            return False
        try:
            return boto3.Session().get_credentials() is not None
        except Exception:
            return False
    except Exception:
        return False


def _reexec_in_backend_container(argv: list[str]) -> int:
    src = Path(__file__).resolve()
    dest = "/tmp/promote_admin.py"
    copied = subprocess.run(
        ["docker", "compose", "cp", str(src), f"backend:{dest}"],
        cwd=ROOT,
    )
    if copied.returncode != 0:
        return copied.returncode
    return subprocess.call(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "-e",
            f"{IN_CONTAINER_ENV}=1",
            "backend",
            "python",
            dest,
            *argv,
        ],
        cwd=ROOT,
    )


def _no_credentials_message(services: set[str]) -> str:
    if "frontend" in services and "backend" not in services:
        return (
            "This host looks like a frontend-only Streamlit instance (no AWS role).\n"
            "SSH to the backend EC2 and run:\n"
            "  python infra/scripts/promote_admin.py --username <name> --yes"
        )
    return (
        "No AWS credentials. Do not run this on frontend Streamlit EC2.\n"
        "SSH to the backend EC2 — instance role retaillen-backend-runtime is "
        "attached to that instance (IMDS), not ~/.aws."
    )


def table():
    import boto3

    name = os.getenv("DDB_USERS_TABLE", "retaillen-users")
    endpoint = os.getenv("DDB_ENDPOINT", "").strip()
    if endpoint:
        region = os.getenv("AWS_REGION", "us-east-1")
        resource = boto3.resource(
            "dynamodb",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or "local",
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or "local",
        )
        return resource.Table(name)

    _ensure_backend_path()
    from core.aws import resource as aws_resource

    return aws_resource("dynamodb").Table(name)


def find_user(users, email: str | None, username: str | None) -> dict | None:
    from boto3.dynamodb.conditions import Key

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


def _session_matches_user(saved: dict, user_id: str) -> bool:
    user = saved.get("user")
    if not isinstance(user, dict):
        return False
    return str(user.get("user_id") or "") == str(user_id)


def _load_redis_url_from_secrets() -> None:
    if os.getenv("REDIS_URL", "").strip():
        return
    if (os.getenv("APP_ENV") or "").strip() != "aws":
        return
    _ensure_backend_path()
    from core.aws import client as aws_client

    name = "retaillen/REDIS_URL"
    try:
        response = aws_client("secretsmanager").get_secret_value(SecretId=name)
    except Exception as exc:
        print(f"could not load {name}: {exc}", file=sys.stderr)
        return
    value = (response.get("SecretString") or "").strip()
    if not value:
        print(f"Secret {name} is empty; Streamlit session cache not updated", file=sys.stderr)
        return
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        value = str(payload.get("REDIS_URL") or "").strip()
    if value:
        os.environ["REDIS_URL"] = value


def refresh_session_cache(user_id: str, is_admin: bool, *, dry_run: bool) -> int:
    """Patch is_admin on Redis Streamlit sessions for this user. Returns match count."""
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        print("REDIS_URL is empty; Streamlit session cache not updated")
        return 0
    try:
        import redis
    except ImportError:
        print(
            "redis package is not installed; Streamlit session cache not updated",
            file=sys.stderr,
        )
        return 0

    try:
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        client.ping()
    except Exception as exc:
        print(f"Redis unreachable; Streamlit session cache not updated: {exc}", file=sys.stderr)
        return 0

    matched = 0
    for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}*", count=100):
        raw = client.get(key)
        if not raw:
            continue
        try:
            saved = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(saved, dict) or not _session_matches_user(saved, user_id):
            continue
        matched += 1
        if dry_run:
            continue
        user = dict(saved.get("user") or {})
        user["is_admin"] = is_admin
        saved["user"] = user
        client.set(key, json.dumps(saved, separators=(",", ":")), keepttl=True)
    return matched


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

    if not _in_backend_container():
        services = _running_compose_services()
        if not _has_aws_credentials():
            if "frontend" in services and "backend" not in services:
                print(_no_credentials_message(services), file=sys.stderr)
                return 2
            if "backend" in services:
                print(
                    "No AWS credentials on this host; retrying inside the backend "
                    "container (same EC2 instance role via IMDS)"
                )
                return _reexec_in_backend_container(sys.argv[1:])
            print(_no_credentials_message(services), file=sys.stderr)
            return 2

    try:
        import boto3  # noqa: F401
    except ImportError:
        if not _in_backend_container() and "backend" in _running_compose_services():
            print("boto3 is not installed on this host; running inside the backend container")
            return _reexec_in_backend_container(sys.argv[1:])
        print(
            "boto3 is not installed. On the backend EC2 use:\n"
            "  backend/.venv/bin/python infra/scripts/promote_admin.py ...",
            file=sys.stderr,
        )
        return 2

    _load_redis_url_from_secrets()
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
        sessions = refresh_session_cache(item["user_id"], flag, dry_run=True)
        print(f"dry-run: no changes (would update {sessions} Redis session(s))")
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
    print("updated DynamoDB")
    sessions = refresh_session_cache(item["user_id"], flag, dry_run=False)
    print(f"updated {sessions} Redis session(s)")
    if sessions == 0:
        print("Streamlit will pick up is_admin from GET /users/me (refresh Account)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        from botocore.exceptions import ClientError

        if isinstance(exc, ClientError):
            print(f"aws error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        raise
