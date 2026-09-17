"""

Adds fields that some existing records predate:
- s3_result_key: S3 path to the report (empty string until the completion Lambda sets it)
- status: pending -> validation -> processing -> done, or failed
- created_at: when the analysis was submitted (best-effort: "now" if truly unknown)
- original_filename: the client's uploaded filename, for the Analysis Library UI
- error_message: set only when status == "failed"

DynamoDB is schemaless, so this is mainly for consistency: new records already include
all of these fields (see backend/api/routers/analyses.py's create_analysis and
backend/shared/models.py's AnalysisItem). This migration only matters for rows that
predate those fields -- without it, list_analyses()/get_analysis() in
backend/api/routers/analyses.py raise a KeyError on any row missing created_at or
original_filename, since those are read with item["..."], not item.get("...").

Run via infra/scripts/run_migrations.py, which calls up(dynamodb) / down(dynamodb) --
this file is not meant to be run standalone.
"""

import os
from datetime import datetime, timezone

# "status" is a reserved word in DynamoDB's expression language and must be aliased
# (see services/analysis_store.py's DynamoAnalysisStore.update() for the same pattern).
_STATUS_ALIAS = {"#status": "status"}


def _legacy_filename(item: dict) -> str:
    """Best-effort display name for rows that predate original_filename."""
    upload_key = item.get("s3_upload_key", "")
    if "." in upload_key:
        return f"legacy_upload.{upload_key.rsplit('.', 1)[-1]}"
    return "unknown"


def up(dynamodb):
    """Add missing tracking fields to existing analyses records."""
    print("Migration: Adding analysis tracking fields to analyses table")
    print("  • s3_result_key")
    print("  • status")
    print("  • created_at")
    print("  • original_filename")
    print("  • error_message")
    print()

    table_name = os.getenv("DDB_ANALYSES_TABLE", "retaillen-analyses")
    table = dynamodb.Table(table_name)

    # Scan for all existing analyses
    response = table.scan()
    items = response.get('Items', [])

    if not items:
        print("No existing records found - table is empty")
        print("Migration complete - new records will include all fields")
        return

    updated_count = 0
    for item in items:
        updates_needed = []
        expression_names = {}
        expression_values = {}

        # Check and add missing fields
        if 's3_result_key' not in item:
            updates_needed.append('s3_result_key = :s3_key')
            expression_values[':s3_key'] = ""  # matches what create_analysis() writes today

        if 'status' not in item:
            updates_needed.append('#status = :status')
            expression_names.update(_STATUS_ALIAS)
            expression_values[':status'] = 'pending'  # Default status

        if 'created_at' not in item:
            updates_needed.append('created_at = :created_at')
            expression_values[':created_at'] = datetime.now(timezone.utc).isoformat()

        if 'original_filename' not in item:
            updates_needed.append('original_filename = :filename')
            expression_values[':filename'] = _legacy_filename(item)

        if 'error_message' not in item:
            updates_needed.append('error_message = :error_message')
            expression_values[':error_message'] = None

        # Update item if any fields are missing
        if updates_needed:
            update_expression = 'SET ' + ', '.join(updates_needed)
            kwargs = {
                "Key": {'analysis_id': item['analysis_id']},
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_values,
            }
            if expression_names:
                kwargs["ExpressionAttributeNames"] = expression_names
            table.update_item(**kwargs)
            updated_count += 1

    print(f"Updated {updated_count} of {len(items)} existing records")
    print("Migration complete!")


def down(dynamodb):
    """Rollback: remove all tracking fields from analyses records."""
    print("Rollback: Removing analysis tracking fields from analyses table")
    print("  • s3_result_key")
    print("  • status")
    print("  • created_at")
    print("  • original_filename")
    print("  • error_message")
    print()

    table_name = os.getenv("DDB_ANALYSES_TABLE", "retaillen-analyses")
    table = dynamodb.Table(table_name)

    response = table.scan()
    items = response.get('Items', [])

    if not items:
        print("No records found - table is empty")
        print("Rollback complete")
        return

    removed_count = 0
    for item in items:
        fields_to_remove = []

        # Check which fields exist and need removal
        for field in ('s3_result_key', 'status', 'created_at', 'original_filename', 'error_message'):
            if field in item:
                fields_to_remove.append(field)

        # Remove all tracked fields at once
        if fields_to_remove:
            remove_expression = 'REMOVE ' + ', '.join(
                '#status' if field == 'status' else field for field in fields_to_remove
            )
            kwargs = {
                "Key": {'analysis_id': item['analysis_id']},
                "UpdateExpression": remove_expression,
            }
            if 'status' in fields_to_remove:
                kwargs["ExpressionAttributeNames"] = _STATUS_ALIAS
            table.update_item(**kwargs)
            removed_count += 1

    print(f"Removed tracking fields from {removed_count} of {len(items)} records")
    print("Rollback complete!")
