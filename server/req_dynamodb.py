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

    if req.type == RequestType.POINT_READ:
        result = point_read(req.params["transport_id"], req.params["stop_id"])
        rows = [result] if result else []
    elif req.type == RequestType.LARGE_SCAN:
        rows = large_scan(req.params["transport_id"], req.params["limit"])
    elif req.type == RequestType.NEXT_DEPARTURES:
        rows = next_departures(req.params["transport_id"], req.params["stop_id"], req.params["after"])
    elif req.type == RequestType.TRIPS_PER_ROUTE:
        rows = trips_per_route(req.params["transport_id"])
    elif req.type == RequestType.BULK_UPDATE_DEPARTURES:
        count = bulk_update_departures(req.params["transport_id"], req.params["trip_id"], req.params["shift"])
        rows = [{"modified": count}]
    else:
        rows = []

    return rows, (time.perf_counter() - t0) * 1000
