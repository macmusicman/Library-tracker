#!/usr/bin/env python3
"""Seed the DynamoDB table with sample inventory items for testing."""
import os
import sys
from decimal import Decimal

import boto3


SAMPLE_ITEMS = [
    {"id": 1, "item_name": "Book 1", "type": "Book", "description": "Chuck Norris Quotes", "on_loan": False, "rating": Decimal("4.5")},
    {"id": 2, "item_name": "Book 2", "type": "Book", "description": "Chuck Norris Wisdom", "on_loan": False, "rating": Decimal("4.0")},
    {"id": 3, "item_name": "DVD 1", "type": "DVD", "description": "Training DVD", "on_loan": False, "rating": Decimal("4.3")},
]


def seed(table_name: str):
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)
    for item in SAMPLE_ITEMS:
        print(f"Putting item id={item['id']}")
        table.put_item(Item=item)


def main():
    table_name = os.environ.get("DYNAMODB_TABLE") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not table_name:
        print("Usage: seed_dynamodb.py <table_name> or set DYNAMODB_TABLE env var")
        sys.exit(2)

    seed(table_name)
    print("Done seeding.")


if __name__ == "__main__":
    main()
