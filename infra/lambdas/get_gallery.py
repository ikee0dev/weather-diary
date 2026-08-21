"""GET /gallery - read endpoint for the frontend. Read-only by design: the
page never triggers generation, EventBridge owns the schedule, so a refresh
costs one DynamoDB query and nothing else.
"""

import json
import os

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["GALLERY_TABLE"]
LIMIT = int(os.environ.get("GALLERY_LIMIT", "60"))

_table = boto3.resource("dynamodb").Table(TABLE_NAME)


def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    items = _table.query(
        KeyConditionExpression=Key("pk").eq("ENTRY"),
        ScanIndexForward=False,
        Limit=LIMIT,
    )["Items"]
    return _resp(200, {"entries": [json.loads(i["body"]) for i in items]})
