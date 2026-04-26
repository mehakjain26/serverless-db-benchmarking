#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
TABLE_NAME = "gtfs"

client = boto3.client("dynamodb", region_name=AWS_REGION)

# ================= DELETE TABLE =================
def delete_table():
    try:
        client.delete_table(TableName=TABLE_NAME)
        print(f"Table '{TABLE_NAME}' deletion initiated. Waiting for it to be removed...")

        waiter = client.get_waiter("table_not_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"Table '{TABLE_NAME}' deleted successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"Table '{TABLE_NAME}' does not exist.")
        else:
            print("Delete failed:", str(e))

if __name__ == "__main__":
    delete_table()
