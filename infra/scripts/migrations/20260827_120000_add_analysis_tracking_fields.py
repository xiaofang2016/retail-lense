"""Add analysis tracking fields to analyses table.

This migration adds the following fields:
- s3_result_key: S3 path to analysis results
- status: Analysis status (pending, processing, completed, failed)
- submitted_date: When the analysis was submitted
- completed_date: When the analysis was completed (null if not done)
"""

import boto3
import os
from datetime import datetime, timezone


def up(dynamodb):
    """
    Adds new attributes to existing analyses records:
    - s3_result_key: S3 path to analysis results
    - status: Analysis status (pending, processing, completed, failed)
    - submitted_date: When the analysis was submitted
    - completed_date: When the analysis was completed (null if not done)
    
    Note: DynamoDB is schemaless, so this is mainly for consistency.
    New records will include these fields, old ones are updated here.
    """
    print("Migration: Adding analysis tracking fields to analyses table")
    print("  • s3_result_key")
    print("  • status")
    print("  • submitted_date")
    print("  • completed_date")

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
        expression_values = {}
        
        # Check and add missing fields
        if 's3_result_key' not in item:
            updates_needed.append('s3_result_key = :s3_key')
            expression_values[':s3_key'] = None
        
        if 'status' not in item:
            updates_needed.append('status = :status')
            expression_values[':status'] = 'pending'  # Default status
        
        if 'submitted_date' not in item:
            # Use created_at if available, otherwise use current time
            submitted = item.get('created_at', datetime.now(timezone.utc).isoformat())
            updates_needed.append('submitted_date = :submitted')
            expression_values[':submitted'] = submitted
        
        if 'completed_date' not in item:
            updates_needed.append('completed_date = :completed')
            expression_values[':completed'] = None
        
        # Update item if any fields are missing
        if updates_needed:
            update_expression = 'SET ' + ', '.join(updates_needed)
            table.update_item(
                Key={'analysis_id': item['analysis_id']},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            updated_count += 1
    
    print(f"Updated {updated_count} existing records")
    print("Migration complete!")


def down(dynamodb):
    """
    Rollback: Remove all tracking fields from analyses records.
    Removes: s3_result_key, status, submitted_date, completed_date
    """
    print("Rollback: Removing analysis tracking fields from analyses table")
    print("  • s3_result_key")
    print("  • status")
    print("  • submitted_date")
    print("  • completed_date")
    print()
    
    table_name = os.getenv("DDB_ANALYSES_TABLE", "retaillen-analyses")
    table = dynamodb.Table(table_name)
    
    response = table.scan()
    items = response.get('Items', [])
    
    if not items:
        print(" No records found - table is empty")
        print("Rollback complete")
        return
    
    removed_count = 0
    for item in items:
        fields_to_remove = []
        
        # Check which fields exist and need removal
        if 's3_result_key' in item:
            fields_to_remove.append('s3_result_key')
        if 'status' in item:
            fields_to_remove.append('status')
        if 'submitted_date' in item:
            fields_to_remove.append('submitted_date')
        if 'completed_date' in item:
            fields_to_remove.append('completed_date')
        
        # Remove all tracked fields at once
        if fields_to_remove:
            remove_expression = 'REMOVE ' + ', '.join(fields_to_remove)
            table.update_item(
                Key={'analysis_id': item['analysis_id']},
                UpdateExpression=remove_expression
            )
            removed_count += 1
    
    print(f" Removed tracking fields from {removed_count} records")
    print(" Rollback complete!")
