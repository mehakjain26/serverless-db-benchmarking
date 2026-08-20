#!/usr/bin/env python3
import csv
import zipfile
import os
import sys
import uuid
import time
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import partial

import boto3

# --- CONFIG ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest-dynamo")
# Silence the verbose boto3/botocore logs
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Optimal defaults for a large GTFS dataset
BATCH_LIMIT = 25
THREAD_WORKERS = 32  # Threads per process
PROCESS_WORKERS = 4  # Matches typical CPU cores

# --- HELPERS ---
def safe_int(x):
    try: return int(x)
    except: return 0

def safe_float(x):
    try: return float(x)
    except: return 0.0

def time_to_sec(t):
    if not t: return 0
    try:
        h, m, s = t.split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except: return 0

# --- UPLOADER WORKER ---
def upload_chunk(profile, region, table_name, items):
    """Worker function to be run in a thread. Uses high-level batch_writer."""
    session = boto3.Session(profile_name=profile, region_name=region)
    db = session.resource("dynamodb")
    table = db.Table(table_name)
    
    count = 0
    with table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
        for item in items:
            batch.put_item(Item=item)
            count += 1
    return count

def process_file(file_path, table_name, transport_id, transform_fn, profile, region):
    """Worker function to be run in a process. Parses CSV and spawns threads."""
    log.info(f"Processing {os.path.basename(file_path)}...")
    
    batches = []
    current_batch = []
    total_parsed = 0
    
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = transform_fn(row, transport_id)
            current_batch.append(item)
            total_parsed += 1
            
            # Group into chunks of ~500 items for thread submission
            if len(current_batch) >= 500:
                batches.append(current_batch)
                current_batch = []
    
    if current_batch:
        batches.append(current_batch)

    log.info(f"Parsed {total_parsed:,} items. Starting upload with threads...")
    
    total_uploaded = 0
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as executor:
        futures = [executor.submit(upload_chunk, profile, region, table_name, b) for b in batches]
        for f in as_completed(futures):
            total_uploaded += f.result()
            
    return total_uploaded

# --- TRANSFORMATIONS ---
def transform_stop(r, tid):
    sid = r.get("stop_id", "")
    return {
        "pk": f"{tid}#stops", "sk": sid, "type": "stops",
        "transport_id": tid, "stop_id": sid,
        "stop_name": r.get("stop_name") or "",
        "stop_lat": r.get("stop_lat"), "stop_lon": r.get("stop_lon")
    }

def transform_route(r, tid):
    rid = r.get("route_id", "")
    return {
        "pk": f"{tid}#routes", "sk": rid, "type": "routes",
        "transport_id": tid, "route_id": rid,
        "route_short_name": r.get("route_short_name") or "",
        "route_color": r.get("route_color") or ""
    }

def transform_trip(r, tid):
    trid = r.get("trip_id", "")
    rid = r.get("route_id", "")
    return {
        "pk": f"{tid}#trips", "sk": trid, "type": "trips",
        "transport_id": tid, "trip_id": trid, "route_id": rid,
        "trip_headsign": r.get("trip_headsign") or "",
        # This mirrors your GSI: gsi_trip (PK=trip_pk)
        "trip_pk": f"{tid}#trip#{trid}"
    }

def transform_stop_time(r, tid):
    trid = r.get("trip_id", "")
    sid = r.get("stop_id", "")
    dep = r.get("departure_time") or "00:00:00"
    uid = uuid.uuid4().hex[:8]
    return {
        "pk": f"{tid}#stop_times", "sk": f"{sid}#{dep}#{uid}", "type": "stop_times",
        "transport_id": tid, "trip_id": trid, "stop_id": sid,
        "departure_time": dep, "arrival_time": r.get("arrival_time") or "00:00:00",
        # GSI: gsi_stop_departure (PK=stop_pk, SK=departure_time)
        "stop_pk": f"{tid}#stop_times#{sid}",
        # GSI: gsi_trip (PK=trip_pk)
        "trip_pk": f"{tid}#trip#{trid}"
    }

# --- MAIN ---
def main():
    p = argparse.ArgumentParser()
    p.add_argument("zip", help="Path to GTFS zip file")
    p.add_argument("transport_id", type=int, help="Transport ID (e.g. 1)")
    p.add_argument("--table", default="gtfs", help="DynamoDB table name")
    p.add_argument("--profile", default=None, help="AWS profile name")
    p.add_argument("--region", default="us-east-1", help="AWS region")
    args = p.parse_args()

    start_time = time.time()
    tmp = f"/tmp/gtfs_{args.transport_id}"
    os.makedirs(tmp, exist_ok=True)

    log.info(f"Extracting {args.zip}...")
    with zipfile.ZipFile(args.zip, "r") as z:
        z.extractall(tmp)

    files_to_process = [
        ("stops.txt", transform_stop),
        ("routes.txt", transform_route),
        ("trips.txt", transform_trip),
        ("stop_times.txt", transform_stop_time),
    ]

    total_all = 0
    for filename, transform in files_to_process:
        path = os.path.join(tmp, filename)
        if not os.path.exists(path):
            log.warning(f"Skipping {filename} (not found)")
            continue
            
        count = process_file(path, args.table, args.transport_id, transform, args.profile, args.region)
        total_all += count
        log.info(f"Successfully loaded {count:,} items from {filename}")

    duration = time.time() - start_time
    log.info(f"FINISHED. Loaded {total_all:,} total items in {duration:.1f}s ({total_all/duration:.1f} items/sec)")

if __name__ == "__main__":
    main()
