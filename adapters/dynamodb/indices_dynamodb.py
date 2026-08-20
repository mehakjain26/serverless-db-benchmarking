#!/usr/bin/env python3

# Creates the DynamoDB table with the required GSIs.
# Run this once before ingesting any data.
#
# Table design (single-table):
#   pk (String) — Partition Key  e.g. "{transport_id}#stops"
#   sk (String) — Sort Key       e.g. "{stop_id}"
#
# GSI 1: gsi_stop_departure  (for next_departures query)
#   PK: stop_pk  (String)  — "{transport_id}#stop_times#{stop_id}"
#   SK: departure_time (String)
#
# GSI 2: gsi_trip  (for bulk_update_departures query)
#   PK: trip_pk  (String)  — "{transport_id}#trip#{trip_id}"
#   SK: sk       (String)

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
TABLE_NAME = "gtfs"

client = boto3.client("dynamodb", region_name=AWS_REGION)


def create_table():
    try:
        client.create_table(
            TableName=TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "pk",             "AttributeType": "S"},
                {"AttributeName": "sk",             "AttributeType": "S"},
                {"AttributeName": "stop_pk",        "AttributeType": "S"},
                {"AttributeName": "departure_time", "AttributeType": "S"},
                {"AttributeName": "trip_pk",        "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "gsi_stop_departure",
                    "KeySchema": [
                        {"AttributeName": "stop_pk",        "KeyType": "HASH"},
                        {"AttributeName": "departure_time", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "gsi_trip",
                    "KeySchema": [
                        {"AttributeName": "trip_pk", "KeyType": "HASH"},
                        {"AttributeName": "sk",      "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        print(f"Table '{TABLE_NAME}' creation initiated. Waiting for it to become ACTIVE...")

        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"Table '{TABLE_NAME}' is now ACTIVE.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{TABLE_NAME}' already exists, skipping creation.")
        else:
            raise


def describe_table():
    resp = client.describe_table(TableName=TABLE_NAME)
    t = resp["Table"]
    print(f"\nTable:  {t['TableName']}")
    print(f"Status: {t['TableStatus']}")
    print(f"Items:  {t['ItemCount']}")
    print("GSIs:")
    for gsi in t.get("GlobalSecondaryIndexes", []):
        keys = {k["AttributeName"]: k["KeyType"] for k in gsi["KeySchema"]}
        print(f"  {gsi['IndexName']}: {keys}  status={gsi['IndexStatus']}")


def main():
    print("Setting up DynamoDB table and indexes...")
    create_table()
    describe_table()
    print("\nAll indexes ready.")


if __name__ == "__main__":
    main()
