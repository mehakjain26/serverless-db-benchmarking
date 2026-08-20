from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import numpy as np

from core import globals as G

rng = np.random.default_rng()


# Using Enum + str mixin for Python < 3.11 compatibility
class RequestType(str, Enum):
    # PK lookup by (transport_id, stop_id). Trivial query — isolates connection
    # and cold-start overhead. Serverless penalty shows most clearly here since
    # the query itself contributes almost nothing to latency.
    POINT_READ = "point_read"

    # 3-way join + index range scan + sort + limit. Represents the flagship
    # "next bus" feature. Tests join planning and index efficiency under
    # concurrent load — serverless may re-plan on each resumed connection.
    NEXT_DEPARTURES = "next_departures"

    # Full-city schedule dump, seq scan + sort, large result set. Stresses I/O
    # throughput and data transfer size. Serverless storage layers (e.g. Neon's
    # disaggregated storage) may show higher latency here vs local disk on
    # traditional instances.
    LARGE_SCAN = "large_scan"

    # GROUP BY + COUNT across a join — CPU-bound aggregation. Tests whether
    # serverless compute throttling or unpredictable CPU allocation causes
    # latency spikes compared to a dedicated traditional instance.
    TRIPS_PER_ROUTE = "trips_per_route"

    # Multi-row UPDATE in one statement — exercises the write path and MVCC.
    # Serverless Postgres architectures that separate compute from storage
    # (WAL shipped over network) may show higher write latency than traditional
    # instances writing to local disk.
    BULK_UPDATE_DEPARTURES = "bulk_update_departures"

    # Triple full-scan aggregation with correlated subquery — maximises CPU
    # pressure without returning data (LIMIT 1). Not included in the random
    # mix; use --op triple_agg to stress compute explicitly.
    TRIPLE_AGG = "triple_agg"


@dataclass
class Request:
    type: RequestType
    params: "dict[str, Any]"


def build(rtype: RequestType, catalog: "list[dict]") -> Request:
    if not catalog:
        return Request(type=rtype, params={})

    # Writes always target catalog[0] so all concurrent users contend on the same rows.
    entry = catalog[0] if rtype is RequestType.BULK_UPDATE_DEPARTURES else catalog[rng.integers(len(catalog))]
    t = entry["transport_id"]
    
    if rtype == RequestType.POINT_READ:
        params = {"transport_id": t, "stop_id": entry["stop_id"]}
    elif rtype == RequestType.NEXT_DEPARTURES:
        params = {
            "transport_id": t,
            "stop_id": entry["stop_id"],
            "after": G.DEPARTURE_AFTER,
        }
    elif rtype == RequestType.LARGE_SCAN:
        params = {"transport_id": t, "limit": G.LARGE_SCAN_LIMIT}
    elif rtype == RequestType.TRIPS_PER_ROUTE:
        params = {"transport_id": t}
    elif rtype == RequestType.BULK_UPDATE_DEPARTURES:
        params = {
            "transport_id": t,
            "trip_id": entry["trip_id"],
            "shift": G.WRITE_SHIFT_SECS,
        }
    elif rtype == RequestType.TRIPLE_AGG:
        params = {"transport_id": t}
    else:
        params = {}
        
    return Request(type=rtype, params=params)
