import argparse

import psycopg2
import rich

from server import db_config as SG

TABLES = [
    """
CREATE TABLE IF NOT EXISTS stops (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_stop_id TEXT,
    stop_name TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    location_type SMALLINT,
    parent_station TEXT
)
""",
    """
CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_route_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    route_type SMALLINT,
    route_color TEXT
)
""",
    """
CREATE TABLE IF NOT EXISTS calendar (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_service_id TEXT,
    monday BOOLEAN,
    tuesday BOOLEAN,
    wednesday BOOLEAN,
    thursday BOOLEAN,
    friday BOOLEAN,
    saturday BOOLEAN,
    sunday BOOLEAN,
    start_date TEXT,
    end_date TEXT
)
""",
    """
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_trip_id TEXT,
    gtfs_route_id TEXT,
    gtfs_service_id TEXT,
    trip_headsign TEXT,
    direction_id SMALLINT
)
""",
    """
CREATE TABLE IF NOT EXISTS stop_times (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_trip_id TEXT,
    gtfs_stop_id TEXT,
    arrival_time INT,
    departure_time INT,
    stop_sequence INT,
    pickup_type SMALLINT,
    drop_off_type SMALLINT
)
""",
]

INDICES = [
    # point_read: PK-style lookup on (transport_id, gtfs_stop_id). UNIQUE also
    # enforces data integrity — no duplicate stops per city.
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_stops ON stops(transport_id, gtfs_stop_id)",
    # next_departures: filters stop_times by stop, then range-scans departure_time
    # and sorts ASC. Composite (transport_id, gtfs_stop_id, departure_time) covers
    # the WHERE and ORDER BY in a single index scan with no extra sort step.
    "CREATE INDEX IF NOT EXISTS idx_st_stop_time ON stop_times(transport_id, gtfs_stop_id, departure_time)",
    # bulk_update_departures: UPDATE stop_times WHERE transport_id + gtfs_trip_id.
    # Kept separate from idx_st_stop_time so the planner picks this tighter index
    # rather than scanning a wider one.
    "CREATE INDEX IF NOT EXISTS idx_st_trip      ON stop_times(transport_id, gtfs_trip_id)",
    # next_departures join: stop_times.gtfs_trip_id -> trips.gtfs_trip_id.
    # Without this, the join would seq-scan the entire trips table per row.
    "CREATE INDEX IF NOT EXISTS idx_trips_trip   ON trips(transport_id, gtfs_trip_id)",
    # trips_per_route join: trips.gtfs_route_id -> routes.gtfs_route_id.
    "CREATE INDEX IF NOT EXISTS idx_trips_route  ON trips(transport_id, gtfs_route_id)",
    # trips_per_route join: routes lookup by gtfs_route_id.
    "CREATE INDEX IF NOT EXISTS idx_routes       ON routes(transport_id, gtfs_route_id)",
    # large_scan: intentionally NO index on departure_time. The ORDER BY forces
    # a sequential scan + sort, which stresses I/O throughput rather than index
    # traversal — that is the point of the operation.
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="postgres", choices=list(SG.POSTGRES_DBS))
    args = p.parse_args()

    rich.print(f"  [dim]db[/dim]  {args.db}")
    conn = psycopg2.connect(**SG.get_postgres(args.db))
    cur = conn.cursor()

    for sql in TABLES:
        label = sql.split("(")[0].strip()
        rich.print(f"  [dim]table[/dim]  {label}")
        cur.execute(sql)
    conn.commit()

    for sql in INDICES:
        label = sql.split("ON ")[1].split(";")[0].strip() if "ON " in sql else sql[:60]
        rich.print(f"  [dim]index[/dim]  {label}")
        cur.execute(sql)
    conn.commit()

    cur.close()
    conn.close()
    rich.print("[green]Done.[/green]")


if __name__ == "__main__":
    main()
