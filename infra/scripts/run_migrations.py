#!/usr/bin/env python3
"""Run DynamoDB migrations in order."""

import os
import sys
from pathlib import Path
import importlib.util
import boto3

# Add backend to path for settings
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from core.settings import get_settings


def load_migration(migration_file: Path):
    """Dynamically load a migration module."""
    spec = importlib.util.spec_from_file_location(migration_file.stem, migration_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_dynamodb_resource():
    """Get boto3 DynamoDB resource based on settings."""
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    
    if settings.ddb_endpoint:
        kwargs["endpoint_url"] = settings.ddb_endpoint
        kwargs["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID") or "local"
        kwargs["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY") or "local"
        return boto3.resource("dynamodb", **kwargs)
    
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        ).resource("dynamodb")
    
    return boto3.resource("dynamodb", **kwargs)


def get_migrations(migrations_dir: Path):
    """Get all migration files in order."""
    migration_files = sorted(migrations_dir.glob("*_*.py"))
    return [f for f in migration_files if f.name != "__init__.py"]


def run_migrations(direction="up"):
    """Run all migrations in the specified direction."""
    settings = get_settings()
    migrations_dir = Path(__file__).parent / "migrations"
    
    print(f"Running migrations ({direction})...")
    print(f"Region: {settings.aws_region}")
    if settings.ddb_endpoint:
        print(f"Endpoint: {settings.ddb_endpoint}")
    if settings.aws_profile:
        print(f"Profile: {settings.aws_profile}")
    print()
    
    dynamodb = get_dynamodb_resource()
    migrations = get_migrations(migrations_dir)
    
    if direction == "down":
        migrations = reversed(migrations)
    
    if not migrations:
        print("No migrations found.")
        return
    
    for migration_file in migrations:
        print(f"{'='*60}")
        print(f"Migration: {migration_file.name}")
        print(f"{'='*60}")
        
        try:
            module = load_migration(migration_file)
            
            if direction == "up" and hasattr(module, "up"):
                module.up(dynamodb)
            elif direction == "down" and hasattr(module, "down"):
                module.down(dynamodb)
            else:
                print(f"⚠️  No {direction}() function found in {migration_file.name}")
            
            print()
        except Exception as e:
            print(f" Error running migration {migration_file.name}: {e}")
            sys.exit(1)
    
    print(f" All migrations completed successfully ({direction})")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run DynamoDB migrations")
    parser.add_argument(
        "--direction",
        choices=["up", "down"],
        default="up",
        help="Migration direction: up (apply) or down (rollback)"
    )
    
    args = parser.parse_args()
    run_migrations(args.direction)


if __name__ == "__main__":
    main()
