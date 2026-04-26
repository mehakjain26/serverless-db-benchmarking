import boto3
import sys

def scan_total(profile, table_name):
    session = boto3.Session(profile_name=profile)
    db = session.client('dynamodb')
    
    total_count = 0
    paginator = db.get_paginator('scan')
    
    print(f"Scanning table: {table_name}...")
    for page in paginator.paginate(TableName=table_name, Select='COUNT'):
        total_count += page['Count']
        sys.stdout.write(f"\rCounted: {total_count:,} items")
        sys.stdout.flush()
    
    print(f"\n\nFINAL TOTAL for {table_name}: {total_count:,}")

if __name__ == "__main__":
    # Check Account B (Remote)
    scan_total('bench-dynamo', 'gtfs')
    
    print("-" * 30)
    
    # Check Account A (Local)
    scan_total('default', 'gtfs')
