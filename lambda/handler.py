import os
import json
from decimal import Decimal

import boto3


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super().default(o)


def _scan_table(table):
    items = []
    resp = table.scan()
    items.extend(resp.get("Items", []))
    # handle pagination
    while resp.get("LastEvaluatedKey"):
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    return items


def _update_item(table, item_id, updates: dict):
    # Build UpdateExpression and ExpressionAttributeValues
    expr = []
    values = {}
    for i, (k, v) in enumerate(updates.items()):
        placeholder = f":v{i}"
        expr.append(f"{k} = {placeholder}")
        values[placeholder] = v

    update_expr = "SET " + ", ".join(expr)
    # DynamoDB expects numeric key type for 'id' if table uses N
    key = {"id": int(item_id)}
    table.update_item(Key=key, UpdateExpression=update_expr, ExpressionAttributeValues=values)


def lambda_handler(event, context):
    table_name = os.environ.get("DYNAMODB_TABLE", "inventory")
    dynamo = boto3.resource("dynamodb")
    table = dynamo.Table(table_name)

    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")

    try:
        if http_method == "GET":
            items = _scan_table(table)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(items, cls=DecimalEncoder),
            }

        if http_method in ("POST", "PUT"):
            body = event.get("body") or ""
            if isinstance(body, str):
                body = json.loads(body) if body else {}

            item_id = body.get("id")
            if item_id is None:
                return {"statusCode": 400, "body": json.dumps({"error": "missing id"})}

            # Only allow updating on_loan for now
            if "on_loan" not in body:
                return {"statusCode": 400, "body": json.dumps({"error": "missing on_loan"})}

            updates = {"on_loan": bool(body["on_loan"])}
            _update_item(table, item_id, updates)

            return {"statusCode": 200, "body": json.dumps({"result": "updated"})}

        return {"statusCode": 405, "body": json.dumps({"error": "method not allowed"})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
