import time

import rich
from pymongo import ASCENDING, MongoClient
from rich.table import Table

from . import db_config as SG
from req_gen import Request, RequestType, build


def get_client() -> MongoClient:
    return MongoClient(
        SG.MONGO["uri"],
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=10000,
        socketTimeoutMS=60000,
        retryWrites=True,
        retryReads=True,
        maxPoolSize=1,
        appname="GTFS-Bench"
    )


def get_col(client: MongoClient):
    return client[SG.MONGO["db"]][SG.MONGO["collection"]]


def point_read(col, params: dict) -> list:
    tid = int(params["transport_id"])
    sid = str(params["stop_id"])
    d = col.find_one(
        {"type": "stops", "transport_id": tid, "stop_id": sid},
        {"_id": 0, "stop_name": 1, "stop_lat": 1, "stop_lon": 1},
    )
    return [d] if d else []


def large_scan(col, params: dict) -> list:
    tid = int(params["transport_id"])
    limit = int(params.get("limit", 100))
    return list(
        col.find(
            {"type": "stop_times", "transport_id": tid},
            {"_id": 0, "trip_id": 1, "stop_id": 1, "departure_time": 1, "arrival_time": 1},
        )
        .sort("departure_time", ASCENDING)
        .limit(limit)
    )


def next_departures(col, params: dict) -> list:
    tid = int(params["transport_id"])
    sid = str(params["stop_id"])
    after = int(params["after"])
    stop_times = list(
        col.find(
            {
                "type": "stop_times",
                "transport_id": tid,
                "stop_id": sid,
                "departure_time": {"$gt": after},
            }
        )
        .sort("departure_time", ASCENDING)
        .limit(20)
    )
    if not stop_times:
        return []

    trip_ids = list({st["trip_id"] for st in stop_times})
    trips = {
        t["trip_id"]: t
        for t in col.find(
            {"type": "trips", "transport_id": tid, "trip_id": {"$in": trip_ids}}
        )
    }
    route_ids = list({t.get("route_id") for t in trips.values() if t.get("route_id")})
    routes = {
        r["route_id"]: r
        for r in col.find(
            {"type": "routes", "transport_id": tid, "route_id": {"$in": route_ids}}
        )
    }

    result = []
    for st in stop_times:
        trip = trips.get(st["trip_id"], {})
        route = routes.get(trip.get("route_id"), {})
        result.append({
            "trip_headsign": trip.get("trip_headsign"),
            "departure_time": st.get("departure_time"),
            "route_short_name": route.get("route_short_name"),
            "route_color": route.get("route_color"),
        })
    return result


def trips_per_route(col, params: dict) -> list:
    tid = int(params["transport_id"])
    pipeline = [
        {"$match": {"type": "trips", "transport_id": tid}},
        {"$group": {"_id": "$route_id", "total_trips": {"$sum": 1}}},
        {"$sort": {"total_trips": -1}},
        {"$limit": 50},
        {
            "$lookup": {
                "from": SG.MONGO["collection"],
                "let": {"rid": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$type", "routes"]},
                                    {"$eq": ["$transport_id", tid]},
                                    {"$eq": ["$route_id", "$$rid"]},
                                ]
                            }
                        }
                    },
                    {"$project": {"_id": 0, "route_short_name": 1}},
                ],
                "as": "route_info",
            }
        },
        {"$unwind": {"path": "$route_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {"_id": 0, "route_short_name": "$route_info.route_short_name", "total_trips": 1}},
    ]
    return list(col.aggregate(pipeline))


def bulk_update_departures(col, params: dict) -> list:
    tid = int(params["transport_id"])
    trip_id = str(params["trip_id"])
    shift = int(params["shift"])
    result = col.update_many(
        {"type": "stop_times", "transport_id": tid, "trip_id": trip_id},
        {"$inc": {"departure_time": shift, "arrival_time": shift}},
    )
    return [{"rowcount": result.modified_count}]


HANDLERS = {
    RequestType.POINT_READ: point_read,
    RequestType.NEXT_DEPARTURES: next_departures,
    RequestType.LARGE_SCAN: large_scan,
    RequestType.TRIPS_PER_ROUTE: trips_per_route,
    RequestType.BULK_UPDATE_DEPARTURES: bulk_update_departures,
}


def execute(col, req: Request) -> tuple[list, float]:
    start = time.perf_counter()
    rows = HANDLERS[req.type](col, req.params)
    latency_ms = (time.perf_counter() - start) * 1000
    return rows, latency_ms


def main():
    import json
    from pathlib import Path

    client = get_client()
    col = get_col(client)
    with open(Path(__file__).parent.parent / "catalog_cache.json") as f:
        catalog = json.load(f)

    t = Table(title="MongoDB benchmark suite", show_lines=False, box=None, pad_edge=False)
    t.add_column("operation", style="bold", min_width=24)
    t.add_column("latency (ms)", justify="right", min_width=12)
    t.add_column("rows", justify="right", min_width=6)

    for rtype in RequestType:
        req = build(rtype, catalog)
        rows, latency = execute(col, req)
        t.add_row(rtype.value, f"{latency:.3f}", str(len(rows)))

    rich.print(t)
    client.close()


if __name__ == "__main__":
    main()
