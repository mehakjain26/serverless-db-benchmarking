import argparse

import rich
from pymongo import ASCENDING, MongoClient

from server import db_config as SG

INDICES = [
    # point_read: PK-style lookup on (type, transport_id, stop_id).
    ("idx_stops_point_read", ["type", "transport_id", "stop_id"]),
    # next_departures: covers WHERE stop + departure_time range + ORDER BY in one scan.
    ("idx_stop_times_departure", ["type", "transport_id", "stop_id", "departure_time"]),
    # bulk_update_departures: UPDATE stop_times WHERE transport_id + trip_id.
    ("idx_stop_times_trip", ["type", "transport_id", "trip_id"]),
    # next_departures join: targeted trip lookup by trip_id.
    ("idx_trips_trip", ["type", "transport_id", "trip_id"]),
    # trips_per_route aggregation: group trips by route_id.
    ("idx_trips_route", ["type", "transport_id", "route_id"]),
    # trips_per_route $lookup: resolve route_id to route name.
    ("idx_routes_route", ["type", "transport_id", "route_id"]),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clear", action="store_true", help="Drop all documents before setting up indices")
    args = p.parse_args()

    client = MongoClient(SG.MONGO["uri"])
    col = client[SG.MONGO["db"]][SG.MONGO["collection"]]

    if args.clear:
        result = col.delete_many({})
        rich.print(f"  [dim]cleared[/dim]  {result.deleted_count} documents")

    for name, fields in INDICES:
        key_pattern = {f: ASCENDING for f in fields}
        existing = col.index_information()
        for existing_name, info in existing.items():
            if dict(info["key"]) == key_pattern and existing_name != name:
                rich.print(f"  [dim]drop conflict[/dim]  {existing_name}")
                col.drop_index(existing_name)
                break
        col.create_index([(f, ASCENDING) for f in fields], name=name)
        rich.print(f"  [dim]index[/dim]  {name}")

    client.close()
    rich.print("[green]Done.[/green]")


if __name__ == "__main__":
    main()
