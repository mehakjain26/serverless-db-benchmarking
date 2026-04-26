#!/usr/bin/env python3

import sys
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Key

import os
AWS_REGION = "us-east-1"
# DYNAMO_TABLE may be a name or a full ARN
DYNAMO_PATH = os.environ.get("DYNAMO_TABLE", "gtfs")
TABLE_NAME = DYNAMO_PATH.split("/")[-1] if "/" in DYNAMO_PATH else DYNAMO_PATH

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMO_PATH)


# ================= HELPERS =================
def query_all(key_cond, **kwargs):
    """Paginate through all results for a Query call."""
    resp = table.query(KeyConditionExpression=key_cond, **kwargs)
    items = resp["Items"]
    while "LastEvaluatedKey" in resp:
        resp = table.query(
            KeyConditionExpression=key_cond,
            ExclusiveStartKey=resp["LastEvaluatedKey"],
            **kwargs,
        )
        items.extend(resp["Items"])
    return items


def minutes_to_time(minutes):
    """Convert integer minutes-from-midnight to 'HH:MM:SS' string."""
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}:00"


def add_minutes_to_time(time_str, shift):
    """Add shift minutes to an 'HH:MM:SS' time string."""
    h, m, s = (int(x) for x in time_str.split(":"))
    total = h * 3600 + m * 60 + s + shift * 60
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


# ================= 1. POINT READ =================
def point_read(transport_id, stop_id):
    resp = table.get_item(
        Key={
            "pk": f"{transport_id}#stops",
            "sk": stop_id,
        }
    )
    d = resp.get("Item")
    if not d:
        return None

    return {
        "stop_name": d.get("stop_name"),
        "lat":       d.get("lat"),
        "lon":       d.get("lon"),
    }


# ================= 2. LARGE SCAN =================
def large_scan(transport_id, limit):
    resp = table.query(
        KeyConditionExpression=Key("pk").eq(f"{transport_id}#stop_times"),
        Limit=limit,
    )
    docs = []
    for d in resp["Items"]:
        docs.append({
            "trip_id":        d.get("trip_id"),
            "stop_id":        d.get("stop_id"),
            "departure_time": d.get("departure_time"),
            "arrival_time":   d.get("arrival_time"),
            "stop_sequence":  d.get("stop_sequence"),
            "pickup_type":    d.get("pickup_type"),
            "drop_off_type":  d.get("drop_off_type"),
        })
    return docs


# ================= 3. NEXT DEPARTURES =================
def next_departures(transport_id, stop_id, after_time):
    # Convert integer minutes to "HH:MM:SS" if needed
    if str(after_time).isdigit():
        after_time_str = minutes_to_time(int(after_time))
    else:
        after_time_str = str(after_time)

    # Query GSI gsi_stop_departure: stop_pk = pk, departure_time > after_time_str
    resp = table.query(
        IndexName="gsi_stop_departure",
        KeyConditionExpression=(
            Key("stop_pk").eq(f"{transport_id}#stop_times#{stop_id}") &
            Key("departure_time").gt(after_time_str)
        ),
        Limit=20,
    )
    stop_times = resp["Items"]

    if not stop_times:
        return []

    # Lookup trips (Direct O(1) lookup using full ARN)
    trip_ids = list({st["trip_id"] for st in stop_times})
    trips = {}
    for tid in trip_ids:
        resp_t = table.get_item(Key={
            "pk": f"{transport_id}#trips", 
            "sk": f"{transport_id}#{tid}"
        })
        if resp_t.get("Item"):
            trips[tid] = resp_t["Item"]

    # Lookup routes (Direct O(1) lookup using full ARN)
    route_ids = list({t.get("route_id") for t in trips.values() if t.get("route_id")})
    routes = {}
    for rid in route_ids:
        resp_r = table.get_item(Key={
            "pk": f"{transport_id}#routes", 
            "sk": rid
        })
        if resp_r.get("Item"):
            routes[rid] = resp_r["Item"]

    result = []
    for st in stop_times:
        trip  = trips.get(st["trip_id"], {})
        route = routes.get(trip.get("route_id", ""), {})
        result.append({
            "headsign":         trip.get("headsign") or trip.get("trip_headsign"),
            "departure_time":   st.get("departure_time"),
            "route_short_name": route.get("short_name") or route.get("route_short_name"),
            "route_color":      route.get("route_color"),
        })

    return result


# ================= 4. TRIPS PER ROUTE =================
def trips_per_route(transport_id):
    # Fetch all trips for this transport_id
    all_trips = query_all(Key("pk").eq(f"{transport_id}#trips"))

    # Count trips per route in Python
    counts = defaultdict(int)
    for t in all_trips:
        counts[t["route_id"]] += 1

    topk = sorted(counts.items(), key=lambda x: -x[1])

    # Look up route details
    result = []
    for route_id, total_trips in topk:
        resp = table.get_item(Key={"pk": f"{transport_id}#routes", "sk": route_id})
        route = resp.get("Item", {})
        result.append({
            "route_short_name": route.get("short_name") or route.get("route_short_name"),
            "total_trips":      total_trips,
        })

    return result


# ================= 5. BULK UPDATE =================
def bulk_update_departures(transport_id, trip_id, shift):
    # Query GSI gsi_trip to find all stop_times for this trip
    resp = table.query(
        IndexName="gsi_trip",
        KeyConditionExpression=Key("trip_pk").eq(f"{transport_id}#trip#{trip_id}"),
    )
    items = resp["Items"]
    while "LastEvaluatedKey" in resp:
        resp = table.query(
            IndexName="gsi_trip",
            KeyConditionExpression=Key("trip_pk").eq(f"{transport_id}#trip#{trip_id}"),
            ExclusiveStartKey=resp["LastEvaluatedKey"],
        )
        items.extend(resp["Items"])

    modified = 0
    for item in items:
        new_dep = add_minutes_to_time(item["departure_time"], shift)
        new_arr = add_minutes_to_time(item["arrival_time"],   shift)

        table.update_item(
            Key={"pk": item["pk"], "sk": item["sk"]},
            UpdateExpression="SET departure_time = :d, arrival_time = :a",
            ExpressionAttributeValues={":d": new_dep, ":a": new_arr},
        )
        modified += 1

    return modified


# ================= MAIN =================
if __name__ == "__main__":
    query_type   = sys.argv[1]
    transport_id = int(sys.argv[2])

    if query_type == "POINT_READ":
        stop_id = sys.argv[3]
        print(point_read(transport_id, stop_id))

    elif query_type == "LARGE_SCAN":
        limit = int(sys.argv[3])
        print(large_scan(transport_id, limit))

    elif query_type == "NEXT_DEPARTURES":
        stop_id    = sys.argv[3]
        after_time = sys.argv[4]
        print(next_departures(transport_id, stop_id, after_time))

    elif query_type == "TRIPS_PER_ROUTE":
        print(trips_per_route(transport_id))

    elif query_type == "BULK_UPDATE_DEPARTURES":
        trip_id = sys.argv[3]
        shift   = int(sys.argv[4])
        print(bulk_update_departures(transport_id, trip_id, shift))

    else:
        print("Unknown query type")
