#!/usr/bin/env python3
"""
Serverless Database Benchmarking Harness (bench.py)

This script automates Locust load-testing runs against various database adapters.
It supports both direct connection benchmarking and serverless HTTP function endpoints,
handling load concurrency levels from 16 to 1024 concurrent users, as well as diurnal traffic shapes.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import rich

from core import globals as G

ROOT = Path(__file__).parent
RESULTS = ROOT / G.RESULTS_DIR

# Map database labels to their respective AWS Lambda HTTP function endpoints
FUNCTION_URLS = {
    "sql": G.FUNCTION_URL_POSTGRES,
    "neon": G.FUNCTION_URL_NEON,
    "ibm_sql": G.FUNCTION_URL_IBM_SQL,
    "cloudant": G.FUNCTION_URL_CLOUDANT,
    "mongo": G.FUNCTION_URL_MONGO,
    "dynamodb": G.FUNCTION_URL_DYNAMODB,
}

# Adapters that reuse another adapter's locustfile with an env override
ADAPTER_ALIASES: Dict[str, Tuple[str, Dict[str, str]]] = {
    "neon": ("sql", {"BENCH_DB": "neon"}),
    "ibm_sql": ("sql", {"BENCH_DB": "ibm_sql"}),
}

OP_CHOICES = [
    "point_read",
    "next_departures",
    "large_scan",
    "trips_per_route",
    "bulk_update_departures",
    "triple_agg",
]


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments for the benchmark runner."""
    p = argparse.ArgumentParser(
        description="Scalability and Performance Analysis of Data Access Patterns in Serverless Applications"
    )
    p.add_argument(
        "--mode",
        choices=["direct", "http"],
        default="direct",
        help="Benchmark direct DB connection vs HTTP Lambda function URL proxy (default: direct)",
    )
    p.add_argument(
        "--adapters",
        nargs="+",
        default=["sql"],
        metavar="ADAPTER",
        help="Target database adapters to test (e.g. sql, neon, ibm_sql, cloudant, mongo, dynamodb)",
    )
    p.add_argument(
        "--users",
        nargs="+",
        type=int,
        default=G.CONCURRENCY_LEVELS,
        metavar="N",
        help="List of concurrent user levels to benchmark (default: defined in globals)",
    )
    p.add_argument(
        "--spawn",
        type=int,
        default=G.SPAWN_RATE,
        help="User spawn rate per second (default: defined in globals)",
    )
    p.add_argument(
        "--time",
        default=G.RUN_TIME,
        help="Duration of each benchmark run (e.g. 2m30s, 5m)",
    )
    p.add_argument(
        "--op",
        choices=OP_CHOICES,
        default=None,
        metavar="OP",
        help="Isolate execution to only this workload query type",
    )
    p.add_argument(
        "--diurnal",
        action="store_true",
        help="Simulate diurnal transit curve load shape instead of fixed concurrency steps",
    )
    p.add_argument(
        "--label",
        default="",
        help="Human-readable prefix name for this benchmark run (used in output titles)",
    )
    for name in FUNCTION_URLS:
        p.add_argument(
            f"--url-{name}",
            default=None,
            metavar="URL",
            help=f"Override default AWS Lambda Function URL for {name}",
        )
    return p.parse_args()


def resolve_url(adapter: str, args: argparse.Namespace) -> str:
    """Resolves target endpoint URL from arguments or global fallbacks."""
    override = getattr(args, f"url_{adapter}", None)
    return override or FUNCTION_URLS.get(adapter, "")


def run_locust(
    adapter: str,
    locustfile: Path,
    host: str,
    users: Optional[int],
    spawn: Optional[int],
    run_time: Optional[str],
    label: str,
    extra_env: Optional[Dict[str, str]] = None,
    diurnal: bool = False,
) -> None:
    """Executes a single headless Locust benchmarking process with the given parameters."""
    csv_path = str(RESULTS / label)
    html_path = str(RESULTS / f"{label}.html")

    # If diurnal shape is selected, load both the adapter locustfile and diurnal script
    locustfile_arg = f"{locustfile.name},{ROOT / 'core' / 'diurnal_shape.py'}" if diurnal else locustfile.name

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        locustfile_arg,
        "--host",
        host,
        "--headless",
        "--csv",
        csv_path,
        "--csv-full-history",
        "--html",
        html_path,
    ]

    if not diurnal:
        cmd += ["-u", str(users), "-r", str(spawn), "--run-time", str(run_time)]

    rich.print(f"\n[bold]{'=' * 60}[/bold]")
    mode_info = "diurnal shape" if diurnal else f"users={users} spawn={spawn} time={run_time}"
    rich.print(f"  [bold]{label}[/bold]  ({mode_info})")
    rich.print(f"  host:   {host}")
    rich.print(f"  output: {csv_path}_stats.csv")
    rich.print(f"[bold]{'=' * 60}[/bold]")

    env = {**os.environ, "PYTHONPATH": str(ROOT), **(extra_env or {})}
    result = subprocess.run(cmd, cwd=locustfile.parent, env=env)
    if result.returncode != 0:
        rich.print(f"  [yellow]WARNING: locust exited with code {result.returncode}[/yellow]", file=sys.stderr)


def main() -> None:
    """Orchestrates benchmark runs across selected adapters and configurations."""
    args = parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    for adapter in args.adapters:
        alias_source, alias_env = ADAPTER_ALIASES.get(adapter, (adapter, {}))
        # Located in reorganized adapters/ folder
        adapter_dir = ROOT / "adapters" / alias_source

        if not adapter_dir.is_dir():
            rich.print(f"[yellow]Skipping {adapter}: {adapter_dir} not found[/yellow]")
            continue

        if args.mode == "direct":
            locustfile = adapter_dir / f"locustfile_{alias_source}.py"
            host = f"direct-{adapter}"
        else:
            locustfile = ROOT / "core" / "locust_base.py"
            host = resolve_url(adapter, args)
            if not host:
                rich.print(f"[yellow]Skipping {adapter} (http): no Lambda URL configuration found. Pass --url-{adapter}[/yellow]")
                continue

        if not locustfile.exists():
            rich.print(f"[yellow]Skipping {adapter}: locustfile {locustfile} not found[/yellow]")
            continue

        slug = args.label.lower().replace(" ", "_") if args.label else ""
        prefix = f"{slug}_" if slug else ""
        run_stem = f"{prefix}{adapter}_{args.mode}"

        if args.label:
            (RESULTS / f"{run_stem}.label").write_text(args.label)

        op_env = {"BENCH_OP": args.op} if args.op else {}

        if args.diurnal:
            run_locust(
                adapter=adapter,
                locustfile=locustfile,
                host=host,
                users=None,
                spawn=None,
                run_time=None,
                label=f"{run_stem}_diurnal",
                extra_env={**alias_env, **op_env},
                diurnal=True,
            )
        else:
            for i, users in enumerate(args.users):
                if i > 0 and G.COOLDOWN_SECS > 0:
                    rich.print(f"\n[dim]Cooling down for {G.COOLDOWN_SECS} seconds...[/dim]")
                    time.sleep(G.COOLDOWN_SECS)
                run_locust(
                    adapter=adapter,
                    locustfile=locustfile,
                    host=host,
                    users=users,
                    spawn=args.spawn,
                    run_time=args.time,
                    label=f"{run_stem}_{users}u",
                    extra_env={**alias_env, **op_env},
                )

    rich.print(f"\n[green]All runs complete.[/green] Results in [bold]{RESULTS}/[/bold]")


if __name__ == "__main__":
    main()
