import time

import rich
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibmcloudant.cloudant_v1 import BulkDocs, CloudantV1
from rich.table import Table

from . import db_config as SG
from req_gen import Request, RequestType, build

DB = SG.CLOUDANT["db"]


def get_client() -> CloudantV1:
    auth = IAMAuthenticator(SG.CLOUDANT["apikey"])
    client = CloudantV1(authenticator=auth)
    client.set_service_url(SG.CLOUDANT["url"])
    return client


def point_read(client: CloudantV1, params: dict) -> list:
    doc_id = f"stop:{params['transport_id']}:{params['stop_id']}"
    return [client.get_document(db=DB, doc_id=doc_id).get_result()]


def next_departures(client: CloudantV1, params: dict) -> list:
    tid = params["transport_id"]
    stop_id = params["stop_id"]
    after = params["after"]

    result = client.post_view(
        db=DB,
        ddoc="stop_times",
        view="by_stop_departure",
        start_key=[tid, stop_id, after],
        end_key=[tid, stop_id, 86400],
        limit=20,
        include_docs=True,
    ).get_result()

    # SQL does this as a 3-way join. Cloudant has no joins, so each trip
    # and route is a separate fetch — this is the honest overhead difference.
    rows = []
    for row in result.get("rows", []):
        doc = row["doc"]
        trip = client.get_document(
            db=DB, doc_id=f"trip:{tid}:{doc['gtfs_trip_id']}"
        ).get_result()
        route = client.get_document(
            db=DB, doc_id=f"route:{tid}:{trip['gtfs_route_id']}"
        ).get_result()
        rows.append({
            "trip_headsign": trip.get("trip_headsign"),
            "departure_time": doc.get("departure_time"),
            "route_short_name": route.get("route_short_name"),
            "route_color": route.get("route_color"),
        })
    return rows


def large_scan(client: CloudantV1, params: dict) -> list:
    result = client.post_view(
        db=DB,
        ddoc="stop_times",
        view="by_transport_departure",
        start_key=[params["transport_id"], 0],
        end_key=[params["transport_id"], 86400],
        limit=params["limit"],
        include_docs=True,
    ).get_result()
    return result.get("rows", [])


def trips_per_route(client: CloudantV1, params: dict) -> list:
    tid = params["transport_id"]

    counts = client.post_view(
        db=DB,
        ddoc="trips",
        view="per_route",
        start_key=[tid, ""],
        end_key=[tid, "\ufff0"],
        group_level=2,
    ).get_result().get("rows", [])

    rows = []
    for row in counts:
        route_id = row["key"][1]
        route = client.get_document(
            db=DB, doc_id=f"route:{tid}:{route_id}"
        ).get_result()
        rows.append({
            "route_short_name": route.get("route_short_name"),
            "total_trips": row["value"],
        })
    return sorted(rows, key=lambda r: r["total_trips"], reverse=True)[:50]


def bulk_update_departures(client: CloudantV1, params: dict) -> list:
    tid = params["transport_id"]
    trip_id = params["trip_id"]
    shift = params["shift"]

    # Cloudant requires read-modify-write since _rev is needed for each update.
    # SQL does this in a single UPDATE statement.
    result = client.post_view(
        db=DB,
        ddoc="stop_times",
        view="by_trip",
        key=[tid, trip_id],
        include_docs=True,
    ).get_result()

    docs = []
    for row in result.get("rows", []):
        doc = row["doc"]
        doc["departure_time"] += shift
        doc["arrival_time"] += shift
        docs.append(doc)

    if docs:
        client.post_bulk_docs(db=DB, bulk_docs=BulkDocs(docs=docs)).get_result()

    return [{"rowcount": len(docs)}]


HANDLERS = {
    RequestType.POINT_READ: point_read,
    RequestType.NEXT_DEPARTURES: next_departures,
    RequestType.LARGE_SCAN: large_scan,
    RequestType.TRIPS_PER_ROUTE: trips_per_route,
    RequestType.BULK_UPDATE_DEPARTURES: bulk_update_departures,
}


def execute(client: CloudantV1, req: Request) -> tuple[list, float]:
    start = time.perf_counter()
    rows = HANDLERS[req.type](client, req.params)
    latency_ms = (time.perf_counter() - start) * 1000
    return rows, latency_ms


def main():
    import json
    from pathlib import Path

    client = get_client()
    with open(Path(__file__).parent.parent / "catalog_cache.json") as f:
        catalog = json.load(f)

    t = Table(title="Cloudant benchmark suite", show_lines=False, box=None, pad_edge=False)
    t.add_column("operation",    style="bold",  min_width=24)
    t.add_column("latency (ms)", justify="right", min_width=12)
    t.add_column("rows",         justify="right", min_width=6)

    for rtype in RequestType:
        req = build(rtype, catalog)
        rows, latency = execute(client, req)
        t.add_row(rtype.value, f"{latency:.3f}", str(len(rows)))

    rich.print(t)


if __name__ == "__main__":
    main()
