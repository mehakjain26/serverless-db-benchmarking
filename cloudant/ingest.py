#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import uuid
import zipfile

from server import db_config as SG
from server.req_cloudant import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()

DB = SG.CLOUDANT["db"]


def extract_zip(zip_file, out_dir):
    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(out_dir)


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def safe_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def time_to_sec(t):
    if not t:
        return 0
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return 0


def bulk_insert(client, docs, batch_size=500):
    for i in range(0, len(docs), batch_size):
        chunk = docs[i:i + batch_size]
        client.post_bulk_docs(db=DB, bulk_docs={"docs": chunk})
        log.info(f"  uploaded {min(i + batch_size, len(docs))}/{len(docs)}")


def ingest(zip_file, city, transport_id):
    log.info(f"Starting {city} (transport_id={transport_id})")

    tmp = "/tmp/gtfs_cloudant"
    os.makedirs(tmp, exist_ok=True)
    extract_zip(zip_file, tmp)

    client = get_client()

    try:
        client.put_database(db=DB)
    except Exception:
        pass

    docs = []

    for r in read_csv(os.path.join(tmp, "stops.txt")):
        stop_id = r.get("stop_id", "")
        docs.append({
            "_id": f"stop:{transport_id}:{stop_id}",
            "type": "stop",
            "transport_id": transport_id,
            "gtfs_stop_id": stop_id,
            "stop_name": r.get("stop_name", ""),
            "stop_lat": safe_float(r.get("stop_lat")),
            "stop_lon": safe_float(r.get("stop_lon")),
            "location_type": safe_int(r.get("location_type")),
            "parent_station": r.get("parent_station", ""),
        })

    for r in read_csv(os.path.join(tmp, "routes.txt")):
        route_id = r.get("route_id", "")
        docs.append({
            "_id": f"route:{transport_id}:{route_id}",
            "type": "route",
            "transport_id": transport_id,
            "gtfs_route_id": route_id,
            "route_short_name": r.get("route_short_name", ""),
            "route_long_name": r.get("route_long_name", ""),
            "route_type": safe_int(r.get("route_type")),
            "route_color": r.get("route_color", ""),
        })

    for r in read_csv(os.path.join(tmp, "trips.txt")):
        trip_id = r.get("trip_id", "")
        docs.append({
            "_id": f"trip:{transport_id}:{trip_id}",
            "type": "trip",
            "transport_id": transport_id,
            "gtfs_trip_id": trip_id,
            "gtfs_route_id": r.get("route_id", ""),
            "gtfs_service_id": r.get("service_id", ""),
            "trip_headsign": r.get("trip_headsign", ""),
            "direction_id": safe_int(r.get("direction_id")),
        })

    for r in read_csv(os.path.join(tmp, "stop_times.txt")):
        docs.append({
            "_id": f"stop_time:{uuid.uuid4().hex}",
            "type": "stop_time",
            "transport_id": transport_id,
            "gtfs_trip_id": r.get("trip_id", ""),
            "gtfs_stop_id": r.get("stop_id", ""),
            "departure_time": time_to_sec(r.get("departure_time")),
            "arrival_time": time_to_sec(r.get("arrival_time")),
            "stop_sequence": safe_int(r.get("stop_sequence")),
            "pickup_type": safe_int(r.get("pickup_type")),
            "drop_off_type": safe_int(r.get("drop_off_type")),
        })

    log.info(f"Uploading {len(docs)} docs...")
    bulk_insert(client, docs)
    log.info(f"Done {city}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("zip_file")
    p.add_argument("city")
    p.add_argument("transport_id", type=int)
    args = p.parse_args()

    ingest(args.zip_file, args.city, args.transport_id)
