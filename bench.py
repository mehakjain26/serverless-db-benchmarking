#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import rich

import globals as G

ROOT = Path(__file__).parent
RESULTS = ROOT / G.RESULTS_DIR

FUNCTION_URLS = {
    "sql": G.FUNCTION_URL_POSTGRES,
    "neon": G.FUNCTION_URL_POSTGRES,
    "cloudant": G.FUNCTION_URL_CLOUDANT,
    "mongo": "",
}

# Adapters that reuse another adapter's locustfile with an env override
ADAPTER_ALIASES = {
    "neon": ("sql", {"BENCH_DB": "neon"}),
}


OP_CHOICES = ["point_read", "next_departures", "large_scan", "trips_per_route", "bulk_update_departures"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["direct", "http"], default="direct")
    p.add_argument("--adapters", nargs="+", default=["sql"], metavar="ADAPTER")
    p.add_argument("--users", nargs="+", type=int, default=G.CONCURRENCY_LEVELS, metavar="N")
    p.add_argument("--spawn", type=int, default=G.SPAWN_RATE)
    p.add_argument("--time", default=G.RUN_TIME)
    p.add_argument("--op", choices=OP_CHOICES, default=None, metavar="OP",
                   help="run only this operation type")
    p.add_argument("--label", default="", help="human-readable name for this run (used in plot titles)")
    for name in FUNCTION_URLS:
        p.add_argument(f"--url-{name}", default=None, metavar="URL")
    return p.parse_args()


def resolve_url(adapter: str, args) -> str:
    return getattr(args, f"url_{adapter}", None) or FUNCTION_URLS.get(adapter, "")


def run_locust(adapter, locustfile, host, users, spawn, run_time, label, extra_env=None):
    csv_path = str(RESULTS / label)
    html_path = str(RESULTS / f"{label}.html")

    cmd = [
        sys.executable, "-m", "locust",
        "-f", locustfile.name,
        "--host", host,
        "-u", str(users),
        "-r", str(spawn),
        "--run-time", run_time,
        "--headless",
        "--csv", csv_path,
        "--csv-full-history",
        "--html", html_path,
    ]

    rich.print(f"\n[bold]{'=' * 60}[/bold]")
    rich.print(f"  [bold]{label}[/bold]  (users={users} spawn={spawn} time={run_time})")
    rich.print(f"  host:   {host}")
    rich.print(f"  output: {csv_path}_stats.csv")
    rich.print(f"[bold]{'=' * 60}[/bold]")

    env = {**os.environ, "PYTHONPATH": str(ROOT), **(extra_env or {})}
    result = subprocess.run(cmd, cwd=locustfile.parent, env=env)
    if result.returncode != 0:
        rich.print(f"  [yellow]WARNING: locust exited {result.returncode}[/yellow]", file=sys.stderr)


def main():
    args = parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    for adapter in args.adapters:
        alias_source, alias_env = ADAPTER_ALIASES.get(adapter, (adapter, {}))
        adapter_dir = ROOT / alias_source

        if not adapter_dir.is_dir():
            rich.print(f"[yellow]Skipping {adapter}: {adapter_dir} not found[/yellow]")
            continue

        if args.mode == "direct":
            locustfile = adapter_dir / f"locustfile_{alias_source}.py"
            host = f"direct-{adapter}"
        else:
            locustfile = ROOT / "locust_base.py"
            host = resolve_url(adapter, args)
            if not host:
                rich.print(f"[yellow]Skipping {adapter} (http): no URL. Pass --url-{adapter}[/yellow]")
                continue

        if not locustfile.exists():
            rich.print(f"[yellow]Skipping {adapter}: {locustfile} not found[/yellow]")
            continue

        slug = args.label.lower().replace(" ", "_") if args.label else ""
        prefix = f"{slug}_" if slug else ""
        run_stem = f"{prefix}{adapter}_{args.mode}"

        if args.label:
            (RESULTS / f"{run_stem}.label").write_text(args.label)

        for i, users in enumerate(args.users):
            if i > 0 and G.COOLDOWN_SECS > 0:
                rich.print(f"\n[dim]Cooling down {G.COOLDOWN_SECS}s...[/dim]")
                time.sleep(G.COOLDOWN_SECS)
            op_env = {"BENCH_OP": args.op} if args.op else {}
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
