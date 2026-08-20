#!/usr/bin/env python3
"""
Cold Start Measurement Utility (cold_start.py)

This script measures and analyzes cold start latency penalties for databases
and serverless functions. It probes connection times, executes a simple query
(point_read) to establish a baseline, idles for a specified duration to allow
connections to drop or serverless containers to recycle, and then captures the
cold invocation latency.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2
import requests
import rich
from rich.rule import Rule
from rich.table import Table

from core import globals as G
from core.req_gen import RequestType, build
from database_clients import db_config as SG

RESULTS_DIR = Path(G.RESULTS_DIR)
OUTPUT_CSV = RESULTS_DIR / "cold_start.csv"


def probe_direct(adapter: str, catalog: List[Dict[str, Any]]) -> float:
    """Probes a direct database connection and measures connection + query latency."""
    # Import modules dynamically to isolate connection dependencies
    from database_clients import req_cloudant, req_dynamodb, req_mongo, req_sql

    req = build(RequestType.POINT_READ, catalog)
    t0 = time.perf_counter()

    if adapter in SG.POSTGRES_DBS:
        creds = dict(SG.get_postgres(adapter))
        if "sslrootcert" in creds:
            # Look inside adapters/sql/ folder for PostgreSQL SSL cert
            cert = Path(__file__).parent / "adapters" / "sql" / creds["sslrootcert"]
            if cert.exists():
                creds["sslrootcert"] = str(cert)
            else:
                # Fallback to database_clients/ folder cert
                client_cert = Path(__file__).parent / "database_clients" / creds["sslrootcert"]
                if client_cert.exists():
                    creds["sslrootcert"] = str(client_cert)

        conn = psycopg2.connect(**creds)
        cur = conn.cursor()
        req_sql.execute(conn, cur, req)
        cur.close()
        conn.close()
    elif adapter == "mongo":
        client = req_mongo.get_client()
        col = req_mongo.get_col(client)
        req_mongo.execute(col, req)
        client.close()
    elif adapter == "cloudant":
        client = req_cloudant.get_client()
        req_cloudant.execute(client, req)
    elif adapter == "dynamodb":
        req_dynamodb.execute(req)
    else:
        raise ValueError(f"Unknown adapter type: {adapter}")

    return (time.perf_counter() - t0) * 1000


def warm_baseline_direct(adapter: str, catalog: List[Dict[str, Any]], reps: int) -> float:
    """Establishes average latency baseline over multiple warm direct database runs."""
    times = []
    for _ in range(reps):
        try:
            times.append(probe_direct(adapter, catalog))
        except Exception as e:
            rich.print(f"    [yellow]Warm baseline probe error: {e}[/yellow]")
    return sum(times) / len(times) if times else 0.0


def probe(url: str, catalog: Dict[str, Any]) -> Tuple[float, float]:
    """Sends HTTP GET request to AWS Lambda Function URL and returns total and internal latencies."""
    params = {
        "op": "point_read",
        "transport_id": catalog["transport_id"],
        "stop_id": catalog["stop_id"],
    }
    t0 = time.perf_counter()
    r = requests.get(url, params=params, timeout=60)
    total_ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()

    # Extract internal database query latency reported by the Lambda itself
    try:
        body = r.json()
        internal_ms = float(body.get("latency_ms", 0.0))
    except (ValueError, TypeError):
        internal_ms = 0.0

    return total_ms, internal_ms


def warm_baseline(url: str, catalog: Dict[str, Any], reps: int) -> Tuple[float, float]:
    """Establishes warm RTT and internal latency baseline over multiple warm HTTP runs."""
    total_times = []
    internal_times = []
    for _ in range(reps):
        try:
            t, i = probe(url, catalog)
            total_times.append(t)
            internal_times.append(i)
        except Exception as e:
            rich.print(f"    [yellow]Warm baseline probe error: {e}[/yellow]")

    avg_total = sum(total_times) / len(total_times) if total_times else 0.0
    avg_internal = sum(internal_times) / len(internal_times) if internal_times else 0.0
    return avg_total, avg_internal


def load_catalog() -> List[Dict[str, Any]]:
    """Loads GTFS transit catalog entries from local cache."""
    with open(Path(__file__).parent / "core" / "catalog_cache.json") as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for cold start benchmark run."""
    p = argparse.ArgumentParser(
        description="Measures container & DB cold start overheads in serverless environments."
    )
    p.add_argument(
        "--service", required=True, help="Service label under evaluation (e.g. Neon, PostgreSQL)"
    )
    p.add_argument(
        "--mode", choices=["http", "direct"], default="http", help="Probing mode (default: http)"
    )
    p.add_argument(
        "--adapter", default=None, help="Database adapter label (required in direct mode)"
    )
    p.add_argument(
        "--url", default=None, help="Target Lambda Function URL endpoint (required in http mode)"
    )
    p.add_argument(
        "--samples", type=int, default=G.COLD_START_SAMPLES, help="Number of cold start probe samples to collect"
    )
    p.add_argument(
        "--idle", type=int, default=G.COLD_START_IDLE_SECS, help="Container idle duration in seconds to trigger cold start"
    )
    p.add_argument(
        "--warm-reps", type=int, default=G.COLD_START_WARM_REPS, help="Repetitions to build warm baseline average"
    )
    return p.parse_args()


def main() -> None:
    """Orchestrates cold start baseline collection and registers results."""
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog()

    if args.mode == "direct":
        if not args.adapter:
            rich.print("[red]--adapter parameter is required for direct connection mode[/red]")
            sys.exit(1)

        rich.print(f"\n[bold]Cold Start Measurement: {args.service} (direct mode)[/bold]")
        rich.print(f"  adapter   = [cyan]{args.adapter}[/cyan]")
        rich.print(f"  samples   = {args.samples}")
        rich.print(f"  idle      = {args.idle}s")
        rich.print(f"  warm_reps = {args.warm_reps}\n")

        rows = []
        for sample_num in range(1, args.samples + 1):
            rich.print(Rule(f"Sample {sample_num}/{args.samples}"))

            rich.print(f"  Warming ({args.warm_reps} reps)...", end=" ")
            warm_ms = warm_baseline_direct(args.adapter, catalog, args.warm_reps)
            rich.print(f"[green]{warm_ms:.1f}ms[/green] average warm latency")

            rich.print(f"\n  [dim]Idling for {args.idle}s to expire connection...[/dim]", end="", flush=True)
            time.sleep(args.idle)
            rich.print(" done.\n")

            rich.print("  Cold probe execution...", end=" ")
            try:
                cold_ms = probe_direct(args.adapter, catalog)
                delta = cold_ms - warm_ms
                color = "red" if delta > 1000 else "yellow" if delta > 200 else "green"
                rich.print(f"[{color}]{cold_ms:.1f} ms[/{color}] (Delta={delta:+.1f} ms)")
            except Exception as e:
                cold_ms = delta = float("nan")
                rich.print(f"[red]FAILED: {e}[/red]")

            rows.append({
                "service": args.service,
                "sample": sample_num,
                "warm_rtt": round(warm_ms, 2),
                "cold_rtt": round(cold_ms, 2),
                "init_overhead": float("nan"),
                "db_wakeup": round(delta, 2) if delta == delta else float("nan"),
            })

    else:
        url = args.url or G.FUNCTION_URL_POSTGRES
        if not url:
            rich.print("[red]No target endpoint URL provided: pass --url or specify FUNCTION_URL_POSTGRES[/red]")
            sys.exit(1)

        rich.print(f"\n[bold]Cold Start Measurement: {args.service} (HTTP Lambda Mode)[/bold]")
        rich.print(f"  url       = [cyan]{url}[/cyan]")
        rich.print(f"  samples   = {args.samples}")
        rich.print(f"  idle      = {args.idle}s")
        rich.print(f"  warm_reps = {args.warm_reps}\n")

        catalog_entry = catalog[0]
        rich.print(f"  stop_id   = [cyan]{catalog_entry['stop_id']}[/cyan]\n")

        rows = []
        for sample_num in range(1, args.samples + 1):
            rich.print(Rule(f"Sample {sample_num}/{args.samples}"))

            rich.print(f"  Warming ({args.warm_reps} reps)...", end=" ")
            warm_total, warm_internal = warm_baseline(url, catalog_entry, args.warm_reps)
            rich.print(f"[green]{warm_total:.1f}ms[/green] RTT ([dim]{warm_internal:.1f}ms internal[/dim])")

            rich.print(f"\n  [dim]Idling for {args.idle}s to recycle container...[/dim]", end="", flush=True)
            time.sleep(args.idle)
            rich.print(" done.\n")

            rich.print("  Cold probe execution...", end=" ")
            try:
                cold_total, cold_internal = probe(url, catalog_entry)
                init_overhead = cold_total - cold_internal
                db_wakeup = cold_internal - warm_internal
                color = "red" if init_overhead > 1000 else "yellow" if init_overhead > 200 else "green"
                rich.print(
                    f"[{color}]{cold_total:.1f} ms[/{color}] "
                    f"(Init={init_overhead:.1f} ms, DB Wakeup={db_wakeup:+.1f} ms)"
                )
            except Exception as e:
                cold_total = cold_internal = init_overhead = db_wakeup = float("nan")
                rich.print(f"[red]FAILED: {e}[/red]")

            rows.append({
                "service": args.service,
                "sample": sample_num,
                "warm_rtt": round(warm_total, 2),
                "cold_rtt": round(cold_total, 2),
                "init_overhead": round(init_overhead, 2),
                "db_wakeup": round(db_wakeup, 2),
            })

    fieldnames = ["service", "sample", "warm_rtt", "cold_rtt", "init_overhead", "db_wakeup"]
    write_header = not OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    t = Table(title="Cold Start Summary Results", show_lines=True)
    t.add_column("Sample", justify="right")
    t.add_column("Warm RTT", justify="right")
    t.add_column("Cold RTT", justify="right")
    t.add_column("Init Overhead (Lambda)", justify="right", style="cyan")
    t.add_column("DB Wakeup", justify="right", style="magenta")

    for r in rows:
        t.add_row(
            str(r["sample"]),
            f"{r['warm_rtt']:.1f}",
            f"{r['cold_rtt']:.1f}",
            f"{r['init_overhead']:.1f}",
            f"{r['db_wakeup']:+.1f}"
        )

    rich.print(t)
    rich.print(f"\nCold start measurements appended to [bold]{OUTPUT_CSV}[/bold]")


if __name__ == "__main__":
    main()
