import os
import csv
import io
import zipfile
import boto3
from tqdm import tqdm

# --- CONFIG ---
TABLE_NAME = "gtfs_bench"
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table(TABLE_NAME)

def ingest_gtfs(zip_path, tid):
    print(f"--- Ingesting {zip_path} into DynamoDB ---")
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        # 1. Stops
        with table.batch_writer() as batch:
            with z.open('stops.txt', 'r') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig'))
                for row in reader:
                    batch.put_item(Item={
                        'PK': f"stop:{tid}:{row['stop_id']}",
                        'SK': "metadata",
                        'type': 'stop',
                        'transport_id': tid,
                        'stop_id': row['stop_id'],
                        'stop_name': row['stop_name'],
                        'stop_lat': row['stop_lat'],
                        'stop_lon': row['stop_lon']
                    })
        print("✅ Stops Ingested")

        # 2. Routes
        with table.batch_writer() as batch:
            with z.open('routes.txt', 'r') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig'))
                for row in reader:
                    batch.put_item(Item={
                        'PK': f"route:{tid}:{row['route_id']}",
                        'SK': "metadata",
                        'type': 'route',
                        'transport_id': tid,
                        'route_id': row['route_id'],
                        'route_short_name': row.get('route_short_name', ''),
                        'route_color': row.get('route_color', '')
                    })
        print("✅ Routes Ingested")

        # 3. Trips
        with table.batch_writer() as batch:
            with z.open('trips.txt', 'r') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig'))
                for row in reader:
                    batch.put_item(Item={
                        'PK': f"trip:{tid}:{row['trip_id']}",
                        'SK': "metadata",
                        'type': 'trips',
                        'transport_id': tid,
                        'trip_id': row['trip_id'],
                        'route_id': row['route_id'],
                        'trip_headsign': row.get('trip_headsign', '')
                    })
        print("✅ Trips Ingested")

        # 4. Stop Times (The biggest file)
        print("Ingesting Stop Times (this may take a while)...")
        with table.batch_writer() as batch:
            with z.open('stop_times.txt', 'r') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig'))
                # We need to find the departure_time column name
                for row in tqdm(reader):
                    # We store stop_times with PK=stop_times:{tid}:{sid} and SK=departure_time
                    # This allows range queries for "Next Departures"
                    dep_time = row['departure_time'].replace(":", "").zfill(6)
                    batch.put_item(Item={
                        'PK': f"stop_times:{tid}:{row['stop_id']}",
                        'SK': dep_time, # Serialized time for sorting
                        'type': 'stop_times',
                        'transport_id': tid,
                        'stop_id': row['stop_id'],
                        'trip_id': row['trip_id'],
                        'arrival_time': row['arrival_time']
                    })
        print("✅ Stop Times Ingested")

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 ingest_dynamo.py <gtfs_zip> <transport_id>")
    else:
        ingest_gtfs(sys.argv[1], int(sys.argv[2]))
