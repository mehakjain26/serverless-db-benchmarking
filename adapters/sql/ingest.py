#!/usr/bin/env python3

import argparse
import csv
import io
import logging
import os
import sys
import zipfile

import psycopg2

from database_clients import db_config as SG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()

# ================= FILES =================
REQUIRED = [
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt"
]

# ================= SAFE CAST HELPERS =================
def i(x):
    return int(x) if x not in (None, "", " ") else 0

def f(x):
    return float(x) if x not in (None, "", " ") else 0.0

def s(x):
    return x if x not in (None, "") else ""

def time_to_sec(t):
    if not t:
        return 0
    try:
        h, m, s = t.split(":")
        return int(h)*3600 + int(m)*60 + int(s)
    except:
        return 0

# ================= EXTRACT =================
def extract(zip_path, out):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out)

    files = {}
    for f in REQUIRED:
        p = os.path.join(out, f)
        if not os.path.exists(p):
            raise Exception(f"Missing {f}")
        files[f] = p
    return files

# ================= COPY =================
def copy(cur, table, path, cols, transform):
    buf = io.StringIO()
    count = 0

    with open(path, "r", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)

        for row in r:
            vals = transform(row)
            buf.write("\t".join(map(str, vals)) + "\n")
            count += 1

    buf.seek(0)

    cur.copy_expert(
        f"COPY {table} ({','.join(cols)}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t')",
        buf
    )

    log.info(f"{table}: {count} rows")

# ================= MAIN =================
def ingest(zip_file, city, transport_id, db="postgres"):

    log.info(f"Starting {city} -> {db}")

    tmp = "/tmp/gtfs"
    os.makedirs(tmp, exist_ok=True)

    files = extract(zip_file, tmp)

    conn = psycopg2.connect(**SG.get_postgres(db))

    with conn:
        with conn.cursor() as cur:

            # ---------------- STOPS ----------------
            copy(
                cur,
                "stops",
                files["stops.txt"],
                ["transport_id","gtfs_stop_id","stop_name","stop_lat","stop_lon","location_type","parent_station"],
                lambda r: [
                    transport_id,
                    s(r.get("stop_id")),
                    s(r.get("stop_name")),
                    f(r.get("stop_lat")),
                    f(r.get("stop_lon")),
                    i(r.get("location_type")),
                    s(r.get("parent_station"))
                ]
            )

            # ---------------- ROUTES ----------------
            copy(
                cur,
                "routes",
                files["routes.txt"],
                ["transport_id","gtfs_route_id","route_short_name","route_long_name","route_type","route_color"],
                lambda r: [
                    transport_id,
                    s(r.get("route_id")),
                    s(r.get("route_short_name")),
                    s(r.get("route_long_name")),
                    i(r.get("route_type")),
                    s(r.get("route_color"))
                ]
            )

            # ---------------- CALENDAR ----------------
            copy(
                cur,
                "calendar",
                files["calendar.txt"],
                ["transport_id","gtfs_service_id","monday","tuesday","wednesday","thursday","friday","saturday","sunday","start_date","end_date"],
                lambda r: [
                    transport_id,
                    s(r.get("service_id")),
                    i(r.get("monday")),
                    i(r.get("tuesday")),
                    i(r.get("wednesday")),
                    i(r.get("thursday")),
                    i(r.get("friday")),
                    i(r.get("saturday")),
                    i(r.get("sunday")),
                    s(r.get("start_date")),
                    s(r.get("end_date"))
                ]
            )

            # ---------------- TRIPS ----------------
            copy(
                cur,
                "trips",
                files["trips.txt"],
                ["transport_id","gtfs_trip_id","gtfs_route_id","gtfs_service_id","trip_headsign","direction_id"],
                lambda r: [
                    transport_id,
                    s(r.get("trip_id")),
                    s(r.get("route_id")),
                    s(r.get("service_id")),
                    s(r.get("trip_headsign")),
                    i(r.get("direction_id"))
                ]
            )

            # ---------------- STOP TIMES ----------------
            copy(
                cur,
                "stop_times",
                files["stop_times.txt"],
                ["transport_id","gtfs_trip_id","gtfs_stop_id","arrival_time","departure_time","stop_sequence","pickup_type","drop_off_type"],
                lambda r: [
                    transport_id,
                    s(r.get("trip_id")),
                    s(r.get("stop_id")),
                    time_to_sec(r.get("arrival_time")),
                    time_to_sec(r.get("departure_time")),
                    i(r.get("stop_sequence")),
                    i(r.get("pickup_type")),
                    i(r.get("drop_off_type"))
                ]
            )

    conn.close()
    log.info(f"Done {city}")

# ================= RUN =================
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("zip_file")
    p.add_argument("city")
    p.add_argument("transport_id", type=int)
    p.add_argument("--db", default="postgres", choices=list(SG.POSTGRES_DBS))
    args = p.parse_args()

    ingest(args.zip_file, args.city, args.transport_id, db=args.db)
