#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import uuid
import zipfile

from pymongo import MongoClient

from database_clients import db_config as SG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()


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


def bulk_insert(col, docs, batch_size=5000):
    for i in range(0, len(docs), batch_size):
        col.insert_many(docs[i:i + batch_size], ordered=False)


def ingest(zip_file, city, transport_id):
    log.info(f"Starting {city} (transport_id={transport_id})")

    tmp = "/tmp/gtfs_mongo"
    os.makedirs(tmp, exist_ok=True)
    extract_zip(zip_file, tmp)

    client = MongoClient(SG.MONGO["uri"])
    col = client[SG.MONGO["db"]][SG.MONGO["collection"]]

    def doc(doc_type, fields):
        return {"_id": f"{doc_type}:{uuid.uuid4().hex}", "type": doc_type,
                "transport_id": transport_id, **fields}

    docs = []

    for r in read_csv(os.path.join(tmp, "stops.txt")):
        docs.append(doc("stops", {
            "stop_id": r.get("stop_id", ""),
            "stop_name": r.get("stop_name", ""),
            "stop_lat": safe_float(r.get("stop_lat")),
            "stop_lon": safe_float(r.get("stop_lon")),
            "location_type": safe_int(r.get("location_type")),
            "parent_station": r.get("parent_station", ""),
        }))

    for r in read_csv(os.path.join(tmp, "routes.txt")):
        docs.append(doc("routes", {
            "route_id": r.get("route_id", ""),
            "route_short_name": r.get("route_short_name", ""),
            "route_long_name": r.get("route_long_name", ""),
            "route_type": safe_int(r.get("route_type")),
            "route_color": r.get("route_color", ""),
        }))

    for r in read_csv(os.path.join(tmp, "trips.txt")):
        docs.append(doc("trips", {
            "trip_id": r.get("trip_id", ""),
            "route_id": r.get("route_id", ""),
            "service_id": r.get("service_id", ""),
            "trip_headsign": r.get("trip_headsign", ""),
            "direction_id": safe_int(r.get("direction_id")),
        }))

    for r in read_csv(os.path.join(tmp, "stop_times.txt")):
        docs.append(doc("stop_times", {
            "trip_id": r.get("trip_id", ""),
            "stop_id": r.get("stop_id", ""),
            "departure_time": time_to_sec(r.get("departure_time")),
            "arrival_time": time_to_sec(r.get("arrival_time")),
            "stop_sequence": safe_int(r.get("stop_sequence")),
            "pickup_type": safe_int(r.get("pickup_type")),
            "drop_off_type": safe_int(r.get("drop_off_type")),
        }))

    log.info(f"Uploading {len(docs)} docs...")
    bulk_insert(col, docs)
    client.close()
    log.info(f"Done {city}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("zip_file")
    p.add_argument("city")
    p.add_argument("transport_id", type=int)
    args = p.parse_args()

    ingest(args.zip_file, args.city, args.transport_id)
