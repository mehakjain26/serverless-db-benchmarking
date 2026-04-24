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


def probe(catalog: dict) -> float:
    params = {
        "op": "point_read",
        "transport_id": catalog["transport_id"],
        "stop_id": catalog["stop_id"],
    }
    t0 = time.perf_counter()
    r = requests.get(G.FUNCTION_URL_POSTGRES, params=params, timeout=60)
    r.raise_for_status()
    return (time.perf_counter() - t0) * 1000


def warm_baseline(catalog: dict, reps: int) -> float:
    times = []
    for _ in range(reps):
        try:
            times.append(probe(catalog))
        except Exception as e:
            rich.print(f"    [yellow]warm probe error: {e}[/yellow]")
    return sum(times) / len(times) if times else float("nan")


def load_catalog() -> list[dict]:
    with open(Path(__file__).parent / "catalog_cache.json") as f:
        return json.load(f)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=G.COLD_START_SAMPLES)
    p.add_argument("--idle", type=int, default=G.COLD_START_IDLE_SECS)
    p.add_argument("--warm-reps", type=int, default=G.COLD_START_WARM_REPS)
    return p.parse_args()


def main():
    args = parse_args()

    if not G.FUNCTION_URL_POSTGRES:
        rich.print("[red]G.FUNCTION_URL_POSTGRES not set in globals.py[/red]")
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rich.print("\n[bold]Cold start measurement[/bold]")
    rich.print(f"  url      = [cyan]{G.FUNCTION_URL_POSTGRES}[/cyan]")
    rich.print(f"  samples  = {args.samples}")
    rich.print(f"  idle     = {args.idle}s")
    rich.print(f"  warm_reps= {args.warm_reps}\n")

    catalog = load_catalog()[0]
    rich.print(f"  stop_id=[cyan]{catalog['stop_id']}[/cyan]\n")

    rows = []

    for sample_num in range(1, args.samples + 1):
        rich.print(Rule(f"Sample {sample_num}/{args.samples}"))

        rich.print(f"  Warming Lambda ({args.warm_reps} reps)...", end=" ")
        warm_avg = warm_baseline(catalog, args.warm_reps)
        rich.print(f"[green]{warm_avg:.1f} ms[/green] avg")

        rich.print(f"\n  [dim]Idling {args.idle}s...[/dim]", end="", flush=True)
        time.sleep(args.idle)
        rich.print("  done.\n")

        rich.print("  Cold probe...", end=" ")
        try:
            cold_ms = probe(catalog)
            delta = cold_ms - warm_avg
            color = "red" if delta > 1000 else "yellow" if delta > 200 else "green"
            rich.print(f"[{color}]{cold_ms:.1f} ms[/{color}]  (delta=[{color}]{delta:+.1f} ms[/{color}])")
        except Exception as e:
            cold_ms = float("nan")
            delta = float("nan")
            rich.print(f"[red]ERROR: {e}[/red]")

        rows.append({
            "sample": sample_num,
            "warm_avg_ms": round(warm_avg, 3),
            "cold_ms": round(cold_ms, 3),
            "delta_ms": round(delta, 3),
        })

    fieldnames = ["sample", "warm_avg_ms", "cold_ms", "delta_ms"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    t = Table(title="Cold Start Summary", show_lines=True)
    t.add_column("Sample", justify="right")
    t.add_column("Warm avg (ms)", justify="right")
    t.add_column("Cold (ms)", justify="right")
    t.add_column("Delta (ms)", justify="right")

    for r in rows:
        delta = r["delta_ms"]
        color = "red" if delta > 1000 else "yellow" if delta > 200 else "green"
        t.add_row(str(r["sample"]), f"{r['warm_avg_ms']:.1f}",
                  f"[{color}]{r['cold_ms']:.1f}[/{color}]",
                  f"[{color}]{delta:+.1f}[/{color}]")

    valid = [r for r in rows if r["cold_ms"] == r["cold_ms"]]
    if valid:
        avg_warm = sum(r["warm_avg_ms"] for r in valid) / len(valid)
        avg_cold = sum(r["cold_ms"] for r in valid) / len(valid)
        avg_delta = sum(r["delta_ms"] for r in valid) / len(valid)
        color = "red" if avg_delta > 1000 else "yellow" if avg_delta > 200 else "green"
        t.add_row("[bold]avg[/bold]", f"[bold]{avg_warm:.1f}[/bold]",
                  f"[bold][{color}]{avg_cold:.1f}[/{color}][/bold]",
                  f"[bold][{color}]{avg_delta:+.1f}[/{color}][/bold]")

    rich.print(t)
    rich.print(f"\nResults written to [bold]{OUTPUT_CSV}[/bold]")


if __name__ == "__main__":
    main()
