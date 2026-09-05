#!/bin/bash
# Helper script for managing local DynamoDB

set -euo pipefail

ENDPOINT="http://localhost:8001"
REGION="us-east-1"

case "${1:-help}" in
  start)
    echo " Starting local DynamoDB..."
    docker compose up -d dynamodb
    echo " DynamoDB running on $ENDPOINT"
    ;;
     
  stop)
    echo "Stopping local DynamoDB..."
    docker compose stop dynamodb

    echo " DynamoDB stopped"
    ;;
    
  restart)
    echo "Restarting local DynamoDB..."
    docker compose restart dynamodb

    echo " DynamoDB restarted"
    ;;
    
  reset)
    echo "⚠️  Resetting local DynamoDB (all data will be lost)..."
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      docker compose down dynamodb
      docker volume rm retail-lense_dynamodb-data || true
      docker compose up -d dynamodb

      echo " DynamoDB reset complete"
    else
      echo " Reset cancelled"
    fi
    ;;
    
  list)
    echo " Listing tables in local DynamoDB..."

    aws dynamodb list-tables --endpoint-url $ENDPOINT --region $REGION
    ;;
    
  create)
    echo "  Creating tables in local DynamoDB..."

    DDB_ENDPOINT=$ENDPOINT python3 infra/scripts/create_dynamodb_tables.py --yes
    ;;
    
  migrate)
    echo " Running migrations..."

    DDB_ENDPOINT=$ENDPOINT python3 infra/scripts/run_migrations.py
    ;;
    
  scan)
    if [ -z "${2:-}" ]; then
      echo " Usage: $0 scan <table-name>"
      exit 1
    fi
    echo " Scanning table: $2"
    aws dynamodb scan --table-name "$2" --endpoint-url $ENDPOINT --region $REGION
    ;;
    
  describe)
    if [ -z "${2:-}" ]; then
      echo " Usage: $0 describe <table-name>"

      exit 1
    fi
    echo " Describing table: $2"
    
    aws dynamodb describe-table --table-name "$2" --endpoint-url $ENDPOINT --region $REGION
    ;;
    
  help|*)
    cat << EOF
Local DynamoDB Management Script

Usage: $0 <command> [options]

Commands:
  start       Start DynamoDB Local container
  stop        Stop DynamoDB Local container
  restart     Restart DynamoDB Local container
  reset       Reset DynamoDB (delete all data and restart)
  list        List all tables
  create      Create all tables (from create_dynamodb_tables.py)
  migrate     Run migrations
  scan        Scan a table (usage: scan <table-name>)
  describe    Describe a table schema (usage: describe <table-name>)
  help        Show this help message

Examples:
  $0 start
  $0 list
  $0 scan retaillen-users
  $0 migrate

DynamoDB Admin UI:
  https://github.com/aaronshaf/dynamodb-admin
  npm install -g dynamodb-admin
  DYNAMO_ENDPOINT=$ENDPOINT dynamodb-admin
EOF
    ;;
esac
