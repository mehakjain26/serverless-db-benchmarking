#!/usr/bin/env python3

import csv
import io
import os
import sys
import zipfile
import aurora_dsql_psycopg2 as dsql
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()

# ================= DSQL CONFIG =================
DSQL_ENDPOINT = os.environ.get("DSQL_ENDPOINT")
DB_REGION = os.environ.get("DB_REGION", "us-east-1")


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
import threading
import queue

def copy(table, path, cols, transform):
    batch_size = 2000 
    num_threads = 16
    
    log.info(f"Ingesting {table} from {path} with {num_threads} threads...")
    
    def worker_pool(q):
        # Create a dedicated connection per thread for high throughput
        worker_conn = dsql.connect(
            host=DSQL_ENDPOINT,
            region=DB_REGION,
            user="admin"
        )
        worker_conn.autocommit = True
        try:
            while True:
                batch_data = q.get()
                if batch_data is None:
                    break
                with worker_conn.cursor() as cur:
                    buf = io.StringIO(batch_data)
                    cur.copy_expert(f"COPY {table} ({','.join(cols)}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t')", buf)
                q.task_done()
        except Exception as e:
            log.error(f"Worker error in {table}: {e}")
        finally:
            worker_conn.close()

    q = queue.Queue(maxsize=num_threads * 2)
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker_pool, args=(q,))
        t.daemon = True
        t.start()
        threads.append(t)

    count = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        batch_lines = []
        for row in r:
            vals = transform(row)
            batch_lines.append("\t".join(map(str, vals)) + "\n")
            count += 1
            if len(batch_lines) >= batch_size:
                q.put("".join(batch_lines))
                batch_lines = []
                if count % 100000 == 0:
                    log.info(f"{table}: queued {count} rows...")
        
        if batch_lines:
            q.put("".join(batch_lines))

    # Signal workers to finish
    for _ in range(num_threads):
        q.put(None)
    
    for t in threads:
        t.join()

    log.info(f"{table}: {count} rows successfully ingested")

# ================= MAIN =================
def ingest(zip_file, city, transport_id):

    log.info(f"Starting {city}")

    tmp = "/tmp/gtfs"
    os.makedirs(tmp, exist_ok=True)

    if not DSQL_ENDPOINT:
        log.error("DSQL_ENDPOINT environment variable not set.")
        return

    files = extract(zip_file, tmp)

    # ---------------- STOPS ----------------
    copy(
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

    log.info(f"Done {city}")

# ================= RUN =================
if __name__ == "__main__":
    zip_file = sys.argv[1]
    city = sys.argv[2]
    transport_id = int(sys.argv[3])

    ingest(zip_file, city, transport_id)