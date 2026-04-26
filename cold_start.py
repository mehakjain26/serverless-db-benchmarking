#!/usr/bin/env python3
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import requests
import rich
from rich.rule import Rule
from rich.table import Table

import globals as G

RESULTS_DIR = Path(G.RESULTS_DIR)
OUTPUT_CSV = RESULTS_DIR / "cold_start.csv"


def probe(url: str, catalog: dict) -> tuple[float, float]:
    params = {
        "op": "point_read",
        "transport_id": catalog["transport_id"],
        "stop_id": catalog["stop_id"],
    }
    t0 = time.perf_counter()
    r = requests.get(url, params=params, timeout=60)
    total_ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    
    # Extract internal latency reported by the Lambda itself
    try:
        body = r.json()
        internal_ms = body.get("latency_ms", 0.0)
    except:
        internal_ms = 0.0
        
    return total_ms, internal_ms


def warm_baseline(url: str, catalog: dict, reps: int) -> tuple[float, float]:
    total_times = []
    internal_times = []
    for _ in range(reps):
        try:
            t, i = probe(url, catalog)
            total_times.append(t)
            internal_times.append(i)
        except Exception as e:
            rich.print(f"    [yellow]warm probe error: {e}[/yellow]")
    
    avg_total = sum(total_times) / len(total_times) if total_times else 0.0
    avg_internal = sum(internal_times) / len(internal_times) if internal_times else 0.0
    return avg_total, avg_internal


def load_catalog() -> list[dict]:
    with open(Path(__file__).parent / "catalog_cache.json") as f:
        return json.load(f)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--service", required=True, help="label for this service (e.g. postgres, neon, gcf)")
    p.add_argument("--url", default=None, help="endpoint URL (defaults to FUNCTION_URL_POSTGRES)")
    p.add_argument("--samples", type=int, default=G.COLD_START_SAMPLES)
    p.add_argument("--idle", type=int, default=G.COLD_START_IDLE_SECS)
    p.add_argument("--warm-reps", type=int, default=G.COLD_START_WARM_REPS)
    return p.parse_args()


def main():
    args = parse_args()
    url = args.url or G.FUNCTION_URL_POSTGRES

    if not url:
        rich.print("[red]No URL: pass --url or set FUNCTION_URL_POSTGRES in globals.py[/red]")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rich.print(f"\n[bold]Cold start measurement: {args.service}[/bold]")
    rich.print(f"  url      = [cyan]{url}[/cyan]")
    rich.print(f"  samples  = {args.samples}")
    rich.print(f"  idle     = {args.idle}s")
    rich.print(f"  warm_reps= {args.warm_reps}\n")

    catalog = load_catalog()[0]
    rich.print(f"  stop_id=[cyan]{catalog['stop_id']}[/cyan]\n")

    rows = []

    for sample_num in range(1, args.samples + 1):
        rich.print(Rule(f"Sample {sample_num}/{args.samples}"))

        rich.print(f"  Warming ({args.warm_reps} reps)...", end=" ")
        warm_total, warm_internal = warm_baseline(url, catalog, args.warm_reps)
        rich.print(f"[green]{warm_total:.1f}ms[/green] RTT ([dim]{warm_internal:.1f}ms internal[/dim])")

        rich.print(f"\n  [dim]Idling {args.idle}s...[/dim]", end="", flush=True)
        time.sleep(args.idle)
        rich.print("  done.\n")

        rich.print("  Cold probe...", end=" ")
        try:
            cold_total, cold_internal = probe(url, catalog)
            
            # Init Overhead = Time spent BEFORE the Lambda code started (Container spin-up)
            init_overhead = cold_total - cold_internal
            
            # DB Wakeup = How much slower the DB query was compared to warm state
            db_wakeup = cold_internal - warm_internal
            
            color = "red" if init_overhead > 1000 else "yellow" if init_overhead > 200 else "green"
            rich.print(f"[{color}]{cold_total:.1f} ms[/{color}]  (Init Overhead=[{color}]{init_overhead:.1f} ms[/{color}], DB Wakeup={db_wakeup:+.1f} ms)")
        except Exception as e:
            cold_total = cold_internal = init_overhead = db_wakeup = float("nan")
            rich.print(f"[red]ERROR: {e}[/red]")

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

    t = Table(title="Cold Start Analysis (High-Res)", show_lines=True)
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
    rich.print(f"\nResults written to [bold]{OUTPUT_CSV}[/bold]")


if __name__ == "__main__":
    main()
