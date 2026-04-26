#!/usr/bin/env python3

import csv
import zipfile
import os
import sys
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

AWS_REGION  = "us-east-1"
TABLE_NAME  = "gtfs"
BATCH_SIZE  = 25    # DynamoDB hard limit per batch_write_item call
MAX_WORKERS = 64    # concurrent batch threads — tune up/down based on WCU headroom

client = boto3.client("dynamodb", region_name=AWS_REGION)

# ================= HELPERS =================
def extract_zip(zip_file, out_dir):
    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(out_dir)

def stream_csv(path):
    """Yield one row dict at a time — avoids loading entire file into memory."""
    with open(path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            yield row

def safe_int(x):
    try:
        return int(x)
    except:
        return 0

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

# ================= PARALLEL UPLOADER =================
_counter_lock = threading.Lock()
_uploaded     = 0
_batches_done = 0

def _send_batch(batch):
    """Send one 25-item batch; retry UnprocessedItems with exponential backoff."""
    global _uploaded, _batches_done
    items_in_batch = len(batch)
    request = {TABLE_NAME: [{"PutRequest": {"Item": item}} for item in batch]}
    delay      = 0.1
    max_retries = 10
    retries    = 0
    while request and retries < max_retries:
        resp = client.batch_write_item(RequestItems=request)
        unprocessed = resp.get("UnprocessedItems", {})
        request = unprocessed if unprocessed else None
        if request:
            retries += 1
            time.sleep(delay)
            delay = min(delay * 2, 5.0)   # cap at 5 s
    with _counter_lock:
        _uploaded     += items_in_batch
        _batches_done += 1

def _to_dynamo(value):
    """Convert a Python value to a DynamoDB-typed dict for the low-level client."""
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, int):
        return {"N": str(value)}
    if isinstance(value, float):
        return {"N": str(value)}
    return {"S": str(value) if value is not None else ""}

def dynamo_item(d):
    """Convert a plain Python dict to DynamoDB attribute map."""
    return {k: _to_dynamo(v) for k, v in d.items()}

def bulk_insert_parallel(rows_iter, label, workers=MAX_WORKERS):
    """
    Stream items from rows_iter, chunk into BATCH_SIZE batches, and
    fire all batches concurrently with a ThreadPoolExecutor.

    Progress is printed every PRINT_EVERY batches completed so the
    output never goes silent while uploads are in flight.
    """
    PRINT_EVERY = 200   # print a progress line every N batches completed

    all_futures   = []
    pending       = []
    last_reported = 0

    def submit_pending(executor):
        for i in range(0, len(pending), BATCH_SIZE):
            chunk = pending[i:i + BATCH_SIZE]
            all_futures.append(executor.submit(_send_batch, [dynamo_item(r) for r in chunk]))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # ---- Phase 1: stream CSV and submit batches ----
        for row in rows_iter:
            pending.append(row)
            if len(pending) >= workers * BATCH_SIZE:
                submit_pending(executor)
                pending.clear()

        if pending:
            submit_pending(executor)
            pending.clear()

        total_batches = len(all_futures)
        print(f"  [{label}] {total_batches:,} batches submitted, waiting for completion...", flush=True)

        # ---- Phase 2: wait and print live progress ----
        for f in as_completed(all_futures):
            f.result()                          # re-raises any exception from the thread
            if _batches_done - last_reported >= PRINT_EVERY:
                last_reported = _batches_done
                print(f"  [{label}] {_batches_done:,}/{total_batches:,} batches done"
                      f"  ({_uploaded:,} items)", flush=True)

    print(f"  [{label}] done — {_uploaded:,} items written")

# ================= INGEST =================
def ingest(zip_file, city, transport_id):
    global _uploaded, _batches_done
    _uploaded     = 0
    _batches_done = 0

    print(f"Starting ingestion for {city} (ID={transport_id})")

    tmp = "/tmp/gtfs_dynamodb"
    os.makedirs(tmp, exist_ok=True)
    extract_zip(zip_file, tmp)

    # ---------------- STOPS ----------------
    def stops_rows():
        for r in stream_csv(os.path.join(tmp, "stops.txt")):
            stop_id = r.get("stop_id", "")
            yield {
                "pk":             f"{transport_id}#stops",
                "sk":             stop_id,
                "type":           "stops",
                "transport_id":   transport_id,
                "stop_id":        stop_id,
                "stop_name":      r.get("stop_name") or "",
                "lat":            str(safe_float(r.get("stop_lat"))),
                "lon":            str(safe_float(r.get("stop_lon"))),
                "location_type":  safe_int(r.get("location_type")),
                "parent_station": r.get("parent_station") or "",
            }

    bulk_insert_parallel(stops_rows(), "stops")

    # ---------------- ROUTES ----------------
    def routes_rows():
        for r in stream_csv(os.path.join(tmp, "routes.txt")):
            route_id = r.get("route_id", "")
            yield {
                "pk":           f"{transport_id}#routes",
                "sk":           route_id,
                "type":         "routes",
                "transport_id": transport_id,
                "route_id":     route_id,
                "short_name":   r.get("route_short_name") or "",
                "long_name":    r.get("route_long_name") or "",
                "route_type":   r.get("route_type") or "",
                "route_color":  r.get("route_color") or "",
            }

    bulk_insert_parallel(routes_rows(), "routes")

    # ---------------- TRIPS ----------------
    def trips_rows():
        for r in stream_csv(os.path.join(tmp, "trips.txt")):
            trip_id  = r.get("trip_id", "")
            route_id = r.get("route_id", "")
            yield {
                "pk":           f"{transport_id}#trips",
                "sk":           f"{route_id}#{trip_id}",
                "type":         "trips",
                "transport_id": transport_id,
                "trip_id":      trip_id,
                "route_id":     route_id,
                "service_id":   r.get("service_id") or "",
                "headsign":     r.get("trip_headsign") or "",
                "direction_id": safe_int(r.get("direction_id")),
            }

    bulk_insert_parallel(trips_rows(), "trips")

    # ---------------- STOP TIMES ----------------
    # Largest file — streamed directly; never fully loaded in memory.
    def stop_times_rows():
        for r in stream_csv(os.path.join(tmp, "stop_times.txt")):
            trip_id        = r.get("trip_id", "")
            stop_id        = r.get("stop_id", "")
            departure_time = r.get("departure_time") or "00:00:00"
            arrival_time   = r.get("arrival_time")   or "00:00:00"
            uid = uuid.uuid4().hex
            yield {
                "pk":             f"{transport_id}#stop_times",
                "sk":             f"{stop_id}#{departure_time}#{uid}",
                "type":           "stop_times",
                "transport_id":   transport_id,
                "trip_id":        trip_id,
                "stop_id":        stop_id,
                "arrival_time":   arrival_time,
                "departure_time": departure_time,
                "stop_sequence":  safe_int(r.get("stop_sequence")),
                "pickup_type":    safe_int(r.get("pickup_type")),
                "drop_off_type":  safe_int(r.get("drop_off_type")),
                "stop_pk":        f"{transport_id}#stop_times#{stop_id}",
                "trip_pk":        f"{transport_id}#trip#{trip_id}",
            }

    bulk_insert_parallel(stop_times_rows(), "stop_times")

    # ---------------- CALENDAR ----------------
    def calendar_rows():
        for r in stream_csv(os.path.join(tmp, "calendar.txt")):
            service_id = r.get("service_id", "")
            yield {
                "pk":           f"{transport_id}#calendar",
                "sk":           service_id,
                "type":         "calendar",
                "transport_id": transport_id,
                "service_id":   service_id,
                "monday":       r.get("monday") or "",
                "tuesday":      r.get("tuesday") or "",
                "wednesday":    r.get("wednesday") or "",
                "thursday":     r.get("thursday") or "",
                "friday":       r.get("friday") or "",
                "saturday":     r.get("saturday") or "",
                "sunday":       r.get("sunday") or "",
                "start_date":   r.get("start_date") or "",
                "end_date":     r.get("end_date") or "",
            }

    bulk_insert_parallel(calendar_rows(), "calendar")

    print(f"\nCompleted ingestion for {city} — {_uploaded:,} total items written")

# ================= MAIN =================
if __name__ == "__main__":
    zip_file     = sys.argv[1]
    city         = sys.argv[2]
    transport_id = int(sys.argv[3])

    ingest(zip_file, city, transport_id)
