# pyright: reportAttributeAccessIssue=false
# pyright: reportGeneralTypeIssues=false

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import rich
from matplotlib.figure import Figure

import globals as G
from diurnal_shape import STAGES

RESULTS_DIR = Path(G.RESULTS_DIR)
FIGURES_DIR = RESULTS_DIR / "figures" / "diurnal"

PCTILE_COLORS = {"p50": "#2196F3", "p95": "#FF9800", "p99": "#F44336"}

PHASE_COLORS = {
    "night_start":  "#BBDEFB",
    "morning_rush": "#FFF9C4",
    "midday":       "#C8E6C9",
    "evening_rush": "#FFE0B2",
    "night_end":    "#BBDEFB",
}

ADAPTER_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]

# Cumulative phase boundaries derived from STAGES
_elapsed = 0
PHASE_BOUNDS: list[dict] = []
for _s in STAGES:
    PHASE_BOUNDS.append({
        "label": _s["label"],
        "start": _elapsed,
        "end": _elapsed + _s["duration"],
        "color": PHASE_COLORS.get(_s["label"], "#F5F5F5"),
    })
    _elapsed += _s["duration"]
TOTAL_DURATION = _elapsed


def load_diurnal_history() -> "dict[str, pd.DataFrame]":
    result = {}
    for path in sorted(RESULTS_DIR.glob("*_diurnal_stats_history.csv")):
        m = re.match(r"(.+_(direct|http))_diurnal_stats_history$", path.stem)
        if not m:
            continue
        df = pd.read_csv(path)
        t0 = df["Timestamp"].min()
        df["elapsed_s"] = df["Timestamp"] - t0
        for col in ["50%", "95%", "99%"]:
            if col in df.columns:
                df[col] = df[col].replace(0, float("nan")).ffill()
        result[m.group(1)] = df
    return result


def load_labels() -> "dict[tuple[str, str], str]":
    labels = {}
    for path in RESULTS_DIR.glob("*.label"):
        m = re.match(r"(.+)_(direct|http)$", path.stem)
        if m:
            labels[(m.group(1), m.group(2))] = path.read_text().strip()
    return labels


def run_label(labels: dict, run_key: str) -> str:
    m = re.match(r"(.+)_(direct|http)$", run_key)
    if m:
        return labels.get((m.group(1), m.group(2)), run_key)
    return run_key


def save(fig: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    rich.print(f"  saved [cyan]{path}[/cyan]")
    plt.close(fig)


def add_phase_bands(axes, alpha: float = 0.18) -> None:
    for ax in axes:
        for phase in PHASE_BOUNDS:
            ax.axvspan(phase["start"], phase["end"], alpha=alpha, color=phase["color"], zorder=0)
        for phase in PHASE_BOUNDS[1:]:
            ax.axvline(phase["start"], color="gray", linewidth=0.5, linestyle=":", zorder=1)


def add_phase_labels(ax) -> None:
    for phase in PHASE_BOUNDS:
        mid = (phase["start"] + phase["end"]) / 2
        ax.text(
            mid, 1.01,
            phase["label"].replace("_", "\n"),
            transform=ax.get_xaxis_transform(),
            ha="center", va="bottom", fontsize=7, color="#555555",
        )


def fig_diurnal_per_adapter(history: dict, labels: dict) -> None:
    """Latency + throughput + user count over time for each adapter separately."""
    for run_key, hdf_full in sorted(history.items()):
        hdf = hdf_full[hdf_full["Name"] == "Aggregated"]
        lbl = run_label(labels, run_key)

        fig, (ax_lat, ax_rps, ax_fail, ax_users) = plt.subplots(
            4, 1, figsize=(12, 11), sharex=True,
            gridspec_kw={"height_ratios": [2, 1, 1, 1]},
        )
        fig.suptitle(f"{lbl}: Diurnal Load Pattern", fontsize=13, fontweight="bold")

        add_phase_bands([ax_lat, ax_rps, ax_fail, ax_users])
        add_phase_labels(ax_lat)

        ax_lat.plot(hdf["elapsed_s"], hdf["50%"], label="p50", linewidth=2, color=PCTILE_COLORS["p50"])
        ax_lat.plot(hdf["elapsed_s"], hdf["95%"], label="p95", linewidth=2, color=PCTILE_COLORS["p95"])
        ax_lat.set_ylabel("latency (ms)", fontsize=11)
        ax_lat.legend(fontsize=10)
        ax_lat.grid(True, axis="y")
        ax_lat.set_ylim(bottom=0)
        ax_lat.set_xlim(0, TOTAL_DURATION)

        ax_rps.plot(hdf["elapsed_s"], hdf["Requests/s"], linewidth=2, color="#55A868")
        ax_rps.set_ylabel("req/s", fontsize=11)
        ax_rps.grid(True, axis="y")
        ax_rps.set_ylim(bottom=0)

        fail_pct = (hdf["Failures/s"] / hdf["Requests/s"].replace(0, float("nan")) * 100).fillna(0)
        ax_fail.plot(hdf["elapsed_s"], fail_pct, linewidth=2, color="#F44336")
        ax_fail.set_ylabel("failure %", fontsize=11)
        ax_fail.grid(True, axis="y")
        ax_fail.set_ylim(0, 100)

        ax_users.plot(hdf["elapsed_s"], hdf["User Count"], linewidth=2, color="#8172B2")
        ax_users.set_xlabel("elapsed (s)", fontsize=11)
        ax_users.set_ylabel("users", fontsize=11)
        ax_users.grid(True, axis="y")
        ax_users.set_ylim(bottom=0)

        fig.tight_layout()
        save(fig, FIGURES_DIR / f"{run_key}_diurnal.png")


def fig_diurnal_comparison(history: dict, labels: dict) -> None:
    """All adapters overlaid on the same axes."""
    if len(history) < 2:
        return

    fig, (ax_lat, ax_rps, ax_fail, ax_users) = plt.subplots(
        4, 1, figsize=(13, 12), sharex=True,
        gridspec_kw={"height_ratios": [2, 1, 1, 1]},
    )
    fig.suptitle("Diurnal Load Pattern: Adapter Comparison", fontsize=13, fontweight="bold")

    add_phase_bands([ax_lat, ax_rps, ax_fail, ax_users])
    add_phase_labels(ax_lat)

    for i, (run_key, hdf_full) in enumerate(sorted(history.items())):
        hdf = hdf_full[hdf_full["Name"] == "Aggregated"]
        lbl = run_label(labels, run_key)
        col = ADAPTER_COLORS[i % len(ADAPTER_COLORS)]

        fail_pct = (hdf["Failures/s"] / hdf["Requests/s"].replace(0, float("nan")) * 100).fillna(0)

        ax_lat.plot(hdf["elapsed_s"], hdf["50%"], label=lbl, linewidth=2, color=col)
        ax_rps.plot(hdf["elapsed_s"], hdf["Requests/s"], label=lbl, linewidth=2, color=col)
        ax_fail.plot(hdf["elapsed_s"], fail_pct, label=lbl, linewidth=2, color=col)
        ax_users.plot(hdf["elapsed_s"], hdf["User Count"], linewidth=2, color=col, label=lbl)

    ax_lat.set_ylabel("p50 latency (ms)", fontsize=11)
    ax_lat.legend(fontsize=9)
    ax_lat.grid(True, axis="y")
    ax_lat.set_ylim(bottom=0)
    ax_lat.set_xlim(0, TOTAL_DURATION)

    ax_rps.set_ylabel("req/s", fontsize=11)
    ax_rps.legend(fontsize=9)
    ax_rps.grid(True, axis="y")
    ax_rps.set_ylim(bottom=0)

    ax_fail.set_ylabel("failure %", fontsize=11)
    ax_fail.legend(fontsize=9)
    ax_fail.grid(True, axis="y")
    ax_fail.set_ylim(0, 100)

    ax_users.set_xlabel("elapsed (s)", fontsize=11)
    ax_users.set_ylabel("users", fontsize=11)
    ax_users.legend(fontsize=9)
    ax_users.grid(True, axis="y")
    ax_users.set_ylim(bottom=0)

    fig.tight_layout()
    save(fig, FIGURES_DIR / "diurnal_comparison.png")


def fig_diurnal_per_op(history: dict, labels: dict) -> None:
    """Per-operation p50 latency over time, one subplot per op, per adapter."""
    OP_ORDER = ["point_read", "next_departures", "large_scan", "trips_per_route", "bulk_update_departures"]

    for run_key, hdf_full in sorted(history.items()):
        lbl = run_label(labels, run_key)
        ops = [op for op in OP_ORDER if op in hdf_full["Name"].values]
        if not ops:
            continue

        ncols = 3
        nrows = -(-len(ops) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows))
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        fig.suptitle(f"{lbl}: Per-Operation Latency (Diurnal)", fontsize=13, fontweight="bold")

        for i, op in enumerate(ops):
            ax = axes_flat[i]
            odf = hdf_full[hdf_full["Name"] == op]
            add_phase_bands([ax])
            ax.plot(odf["elapsed_s"], odf["50%"], label="p50", linewidth=2, color=PCTILE_COLORS["p50"])
            ax.plot(odf["elapsed_s"], odf["95%"], label="p95", linewidth=2, color=PCTILE_COLORS["p95"])
            ax.set_title(op.replace("_", " ").title(), fontsize=10)
            ax.set_xlabel("elapsed (s)", fontsize=9)
            ax.set_ylabel("latency (ms)", fontsize=9)
            ax.legend(fontsize=8)
            ax.grid(True, axis="y")
            ax.set_ylim(bottom=0)
            ax.set_xlim(0, TOTAL_DURATION)

        for j in range(len(ops), len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.tight_layout()
        save(fig, FIGURES_DIR / f"{run_key}_per_op.png")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--no-show", action="store_true")
    p.parse_args()

    history = load_diurnal_history()
    if not history:
        rich.print(f"[red]No diurnal results found in {RESULTS_DIR}/.[/red]")
        rich.print("  Run bench.py with [bold]--diurnal[/bold] first.")
        return

    labels = load_labels()
    rich.print(f"\n[bold]Loaded {len(history)} diurnal run(s):[/bold]")
    for key in sorted(history):
        rich.print(f"  {run_label(labels, key)}")
    rich.print()

    for fn in [
        lambda: fig_diurnal_per_adapter(history, labels),
        lambda: fig_diurnal_comparison(history, labels),
        lambda: fig_diurnal_per_op(history, labels),
    ]:
        try:
            fn()
        except Exception as e:
            rich.print(f"  [yellow]warning: chart skipped - {e}[/yellow]")

    rich.print(f"\n[green]Done.[/green] Figures in [bold]{FIGURES_DIR}/[/bold]")


if __name__ == "__main__":
    main()
