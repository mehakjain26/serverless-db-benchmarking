# pyright: reportIndexIssue=false
# pyright: reportOptionalSubscript=false
import argparse

import rich
from ibmcloudant.cloudant_v1 import DesignDocument, DesignDocumentViewsMapReduce

from database_clients.req_cloudant import DB, get_client

DESIGN_DOCS = {
    "stop_times": {
        # next_departures: composite key (transport_id, gtfs_stop_id, departure_time)
        # allows a range scan to find all departures from a stop after a given time,
        # ordered by departure_time. Mirrors idx_st_stop_time in SQL.
        "by_stop_departure": {
            "map": """function(doc) {
                if (doc.type === 'stop_time') {
                    emit([doc.transport_id, doc.gtfs_stop_id, doc.departure_time], null);
                }
            }""",
        },
        # bulk_update_departures: fetches all stop_times for a given trip so they
        # can be read and rewritten. Cloudant has no UPDATE, it requires a
        # read-modify-write cycle, so this view is the fetch step.
        # Mirrors idx_st_trip in SQL.
        "by_trip": {
            "map": """function(doc) {
                if (doc.type === 'stop_time') {
                    emit([doc.transport_id, doc.gtfs_trip_id], null);
                }
            }""",
        },
        # large_scan: returns all stop_times for a city ordered by departure_time.
        # Like SQL, no tighter index is used here, it the full scan is the point,
        # stressing I/O throughput rather than index lookup speed.
        "by_transport_departure": {
            "map": """function(doc) {
                if (doc.type === 'stop_time') {
                    emit([doc.transport_id, doc.departure_time], null);
                }
            }""",
        },
    },
    "trips": {
        # trips_per_route: counts trips grouped by (transport_id, gtfs_route_id).
        # The _count reduce is pre-computed incrementally on every write, so reads
        # are O(1) regardless of dataset size. This is a key structural difference
        # from SQL which recomputes GROUP BY at query time.
        "per_route": {
            "map": """function(doc) {
                if (doc.type === 'trip') {
                    emit([doc.transport_id, doc.gtfs_route_id], 1);
                }
            }""",
            "reduce": "_count",
        },
    },
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clear", action="store_true", help="Delete and recreate the database before setting up design docs")
    args = p.parse_args()

    client = get_client()

    if args.clear:
        try:
            client.delete_database(db=DB)
            rich.print(f"  [dim]deleted[/dim]  database '{DB}'")
        except Exception:
            rich.print(f"  [dim]not found[/dim]  database '{DB}'")

    try:
        client.put_database(db=DB)
        rich.print(f"  [dim]created[/dim]  database '{DB}'")
    except Exception:
        rich.print(f"  [dim]exists[/dim]   database '{DB}'")

    for ddoc_name, views in DESIGN_DOCS.items():
        built_views = {}
        for view_name, view_def in views.items():
            built_views[view_name] = DesignDocumentViewsMapReduce(
                map=view_def["map"],
                reduce=view_def.get("reduce"),
            )

        from ibm_cloud_sdk_core.api_exception import ApiException
        rev = None
        action = "created"
        try:
            existing = client.get_design_document(db=DB, ddoc=ddoc_name).get_result()
            rev = existing.get("_rev")
            action = "updated"
        except ApiException as e:
            if e.status_code != 404:
                raise

        ddoc = DesignDocument(views=built_views)
        kwargs = {"if_match": rev} if rev else {}
        client.put_design_document(db=DB, ddoc=ddoc_name, design_document=ddoc, **kwargs)
        rich.print(f"  [dim]{action}[/dim]  _design/{ddoc_name}")

    rich.print("[green]Done.[/green]")


if __name__ == "__main__":
    main()
