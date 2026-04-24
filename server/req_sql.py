import time

import psycopg2
import psycopg2.extensions as pe
import rich
from rich.table import Table

from req_gen import Request, RequestType, build

from . import db_config as SG

SQL = {
    RequestType.POINT_READ: """
        SELECT stop_name, stop_lat, stop_lon
        FROM stops
        WHERE transport_id = %(transport_id)s
          AND gtfs_stop_id = %(stop_id)s;
    """,
    RequestType.LARGE_SCAN: """
        SELECT gtfs_trip_id, gtfs_stop_id, departure_time, arrival_time
        FROM stop_times
        WHERE transport_id = %(transport_id)s
        ORDER BY departure_time
        LIMIT %(limit)s;
    """,
    RequestType.NEXT_DEPARTURES: """
        SELECT t.trip_headsign, st.departure_time,
               r.route_short_name, r.route_color
        FROM stop_times st
        JOIN trips  t ON st.gtfs_trip_id = t.gtfs_trip_id
                     AND st.transport_id = t.transport_id
        JOIN routes r ON t.gtfs_route_id = r.gtfs_route_id
                     AND t.transport_id  = r.transport_id
        WHERE st.transport_id  = %(transport_id)s
          AND st.gtfs_stop_id  = %(stop_id)s
          AND st.departure_time > %(after)s
        ORDER BY st.departure_time ASC
        LIMIT 20;
    """,
    RequestType.TRIPS_PER_ROUTE: """
        SELECT r.route_short_name, COUNT(t.id) AS total_trips
        FROM routes r
        JOIN trips t ON r.gtfs_route_id = t.gtfs_route_id
                    AND r.transport_id  = t.transport_id
        WHERE r.transport_id = %(transport_id)s
        GROUP BY r.route_short_name
        ORDER BY total_trips DESC
        LIMIT 50;
    """,
    RequestType.BULK_UPDATE_DEPARTURES: """
        UPDATE stop_times
        SET departure_time = departure_time + %(shift)s,
            arrival_time   = arrival_time   + %(shift)s
        WHERE transport_id = %(transport_id)s
          AND gtfs_trip_id = %(trip_id)s;
    """,
}

WRITES = {RequestType.BULK_UPDATE_DEPARTURES}


def execute(conn: pe.connection, cur: pe.cursor, req: Request) -> tuple[list, float]:
    start = time.perf_counter()
    cur.execute(SQL[req.type], req.params)
    if req.type in WRITES:
        conn.commit()
        rows = [{"rowcount": cur.rowcount}]
    else:
        rows = cur.fetchall()
    latency_ms = (time.perf_counter() - start) * 1000
    return rows, latency_ms


def main():
    import json
    from pathlib import Path

    conn: pe.connection = psycopg2.connect(**SG.POSTGRES)
    cur: pe.cursor = conn.cursor()

    with open(Path(__file__).parent.parent / "catalog_cache.json") as f:
        catalog = json.load(f)

    t = Table(title="SQL benchmark suite", show_lines=False, box=None, pad_edge=False)
    t.add_column("operation", style="bold", min_width=24)
    t.add_column("latency (ms)", justify="right", min_width=12)
    t.add_column("rows", justify="right", min_width=6)

    for rtype in RequestType:
        req = build(rtype, catalog)
        rows, latency = execute(conn, cur, req)
        t.add_row(rtype.value, f"{latency:.3f}", str(len(rows)))

    rich.print(t)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
