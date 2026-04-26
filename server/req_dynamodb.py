import time

from dynamodb.query_dynamodb import (
    bulk_update_departures,
    large_scan,
    next_departures,
    point_read,
    trips_per_route,
)
from req_gen import Request, RequestType


def execute(req: Request) -> "tuple[list, float]":
    t0 = time.perf_counter()

    # Cast numeric parameters
    tid = int(req.params.get("transport_id", 1))

    if req.type == RequestType.POINT_READ:
        result = point_read(tid, req.params.get("stop_id", ""))
        rows = [result] if result else []
    elif req.type == RequestType.LARGE_SCAN:
        limit = int(req.params.get("limit", 100))
        rows = large_scan(tid, limit)
    elif req.type == RequestType.NEXT_DEPARTURES:
        rows = next_departures(tid, req.params.get("stop_id", ""), req.params.get("after", "00:00:00"))
    elif req.type == RequestType.TRIPS_PER_ROUTE:
        rows = trips_per_route(tid)
    elif req.type == RequestType.BULK_UPDATE_DEPARTURES:
        shift = int(req.params.get("shift", 0))
        count = bulk_update_departures(tid, req.params.get("trip_id", ""), shift)
        rows = [{"modified": count}]
    else:
        rows = []

    return rows, (time.perf_counter() - t0) * 1000
