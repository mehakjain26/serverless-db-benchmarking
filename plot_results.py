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
from diurnal_shape import STAGES as DIURNAL_STAGES

RESULTS_DIR = Path(G.RESULTS_DIR)
FIGURES_DIR = RESULTS_DIR / "figures"

PCTILE_COLORS = {"p50": "#2196F3", "p95": "#FF9800", "p99": "#F44336"}

OP_COLORS = {
    "point_read": "#4C72B0",
    "next_departures": "#DD8452",
    "large_scan": "#55A868",
    "trips_per_route": "#C44E52",
    "bulk_update_departures": "#8172B2",
}
OP_ORDER = list(OP_COLORS)


def load_stats() -> pd.DataFrame:
    rows = []
    for path in sorted(RESULTS_DIR.glob("*_stats.csv")):
        m = re.match(r"(.+)_(direct|http)_(\d+)u_stats$", path.stem)
        if not m:
            continue
        adapter, mode, users = m.group(1), m.group(2), int(m.group(3))
        df = pd.read_csv(path)
        df = df[df["Name"] != "Aggregated"].copy()
        for _, row in df.iterrows():
            rows.append(
                {
                    "adapter": adapter,
                    "mode": mode,
                    "users": users,
                    "op": row["Name"],
                    "p50": row["50%"],
                    "p95": row["95%"],
                    "p99": row["99%"],
                    "rps": row["Requests/s"],
                    "failures": row["Failure Count"],
                    "requests": row["Request Count"],
                    "avg_ms": row["Average Response Time"],
                    "success_rps": row["Requests/s"] * (
                        1 - row["Failure Count"] / row["Request Count"]
                        if row["Request Count"] > 0 else 0
                    ),
                }
            )
    return pd.DataFrame(rows)


def load_labels() -> "dict[tuple[str, str], str]":
    labels = {}
    for path in RESULTS_DIR.glob("*.label"):
        m = re.match(r"(.+)_(direct|http)$", path.stem)
        if m:
            labels[(m.group(1), m.group(2))] = path.read_text().strip()
    return labels


def load_history() -> "dict[str, pd.DataFrame]":
    result = {}
    for path in sorted(RESULTS_DIR.glob("*_stats_history.csv")):
        m = re.match(r"(.+_(?:direct|http)_\d+u)_stats_history$", path.stem)
        if not m:
            continue
        df = pd.read_csv(path)
        t0 = df["Timestamp"].min()
        df["elapsed_s"] = df["Timestamp"] - t0
        pct_cols = ["50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%"]
        for col in pct_cols:
            if col in df.columns:
                df[col] = df[col].replace(0, float("nan")).ffill()
        result[m.group(1)] = df
    return result


def subdir(name: str) -> Path:
    d = FIGURES_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(fig: Figure, path: Path, show: bool) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    rich.print(f"  saved [cyan]{path}[/cyan]")
    plt.close(fig)


def ops_present(df: pd.DataFrame) -> list[str]:
    return [op for op in OP_ORDER if op in df["op"].values]


def label_points(ax, x, y, fmt="{:.0f}") -> None:
    for xi, yi in zip(x, y):
        ax.annotate(
            fmt.format(yi),
            xy=(xi, yi),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def run_label(labels: "dict[tuple[str,str],str]", adapter: str, mode: str) -> str:
    return labels.get((adapter, mode), f"{adapter} {mode}")


def latency_ax(ax, odf: pd.DataFrame, users_sorted: list, subtitle: str) -> None:
    pctiles = list(PCTILE_COLORS.keys())
    bar_w = 0.8 / len(pctiles)
    x = range(len(users_sorted))
    for i, (pctile, col) in enumerate(PCTILE_COLORS.items()):
        offset = (i - (len(pctiles) - 1) / 2) * bar_w
        vals = [
            odf[odf["users"] == u][pctile].values[0] if u in odf["users"].values else 0
            for u in users_sorted
        ]
        bars = ax.bar(
            [xi + offset for xi in x], vals, width=bar_w, color=col, label=pctile
        )
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1,
                    f"{val:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(u) for u in users_sorted], fontsize=9)
    ax.set_title(subtitle, fontsize=10)
    ax.set_xlabel("concurrent users", fontsize=9)
    ax.set_ylabel("latency (ms)", fontsize=9)
    ax.legend(fontsize=8)
    ax.set_axisbelow(True)
    ax.grid(True, axis="y")
    ax.set_ylim(bottom=0)


def fig_latency_vs_concurrency(df: pd.DataFrame, labels: dict, show: bool) -> None:
    out = subdir("latency_vs_concurrency")
    for (adapter, mode), mdf in df.groupby(["adapter", "mode"]):
        lbl = run_label(labels, adapter, mode)
        ops = ops_present(mdf)
        users_sorted = sorted(mdf["users"].unique())
        ncols = 3
        nrows = -(-len(ops) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4 * nrows))
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        fig.suptitle(
            f"{lbl}: Latency Percentiles vs Concurrency", fontsize=13, fontweight="bold"
        )

        for i, op in enumerate(ops):
            odf = mdf[mdf["op"] == op].sort_values("users")  # pyright: ignore[reportCallIssue]
            latency_ax(axes_flat[i], odf, users_sorted, op.replace("_", " ").title())

        for j in range(len(ops), len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.tight_layout()
        save(fig, out / f"{adapter}_{mode}_per_op.png", show)


def fig_latency_avg(df: pd.DataFrame, labels: dict, show: bool) -> None:
    out = subdir("latency_vs_concurrency")
    for (adapter, mode), mdf in df.groupby(["adapter", "mode"]):
        lbl = run_label(labels, adapter, mode)
        users_sorted = sorted(mdf["users"].unique())
        avg = (
            mdf.groupby("users")[["p50", "p95", "p99"]]
            .mean()
            .reset_index()
            .sort_values("users")
        )

        fig, ax = plt.subplots(figsize=(7, 4))
        fig.suptitle(
            f"{lbl}: Average Latency vs Concurrency", fontsize=13, fontweight="bold"
        )
        latency_ax(ax, avg, users_sorted, "Mean Across All Operations")
        fig.tight_layout()
        save(fig, out / f"{adapter}_{mode}_average.png", show)


def fig_latency_bars(df: pd.DataFrame, labels: dict, show: bool) -> None:
    out = subdir("latency_bars")
    for (adapter, mode), mdf in df.groupby(["adapter", "mode"]):
        lbl = run_label(labels, adapter, mode)
        ops = ops_present(mdf)
        user_levels = sorted(mdf["users"].unique())
        bar_w = 0.8 / len(user_levels)
        x = range(len(ops))

        fig, ax = plt.subplots(figsize=(max(8, 2 * len(ops)), 5))
        fig.suptitle(f"{lbl}: P95 Latency by Operation", fontsize=13, fontweight="bold")

        for li, users in enumerate(user_levels):
            udf = mdf[mdf["users"] == users]
            vals = [
                udf[udf["op"] == op]["p95"].values[0] if op in udf["op"].values else 0
                for op in ops
            ]
            offset = (li - (len(user_levels) - 1) / 2) * bar_w
            bars = ax.bar(
                [xi + offset for xi in x], vals, width=bar_w, label=f"{users} users"
            )
            for bar, val in zip(bars, vals):
                if val > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 1,
                        f"{val:.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

        ax.set_xticks(list(x))
        ax.set_xticklabels([op.replace("_", "\n") for op in ops], fontsize=9)
        ax.set_ylabel("p95 latency (ms)", fontsize=11)
        ax.legend(title="concurrency", fontsize=9)
        ax.set_axisbelow(True)
        ax.grid(True, axis="y")
        ax.set_ylim(bottom=0)
        fig.tight_layout()
        save(fig, out / f"{adapter}_{mode}.png", show)


def fig_throughput(df: pd.DataFrame, labels: dict, show: bool) -> None:
    out = subdir("throughput")
    agg = df.groupby(["adapter", "mode", "users"])[["rps", "success_rps"]].mean().reset_index()

    for (adapter, mode), mdf in agg.groupby(["adapter", "mode"]):
        lbl = run_label(labels, adapter, mode)
        fig, ax = plt.subplots(figsize=(7, 4))
        fig.suptitle(
            f"{lbl}: Throughput vs Concurrency", fontsize=13, fontweight="bold"
        )

        mdf = mdf.sort_values("users")
        x = [str(u) for u in mdf["users"]]
        bar_w = 0.35
        xi = range(len(x))
        bars_total = ax.bar(
            [i - bar_w / 2 for i in xi], mdf["rps"], width=bar_w,
            color="#4C72B0", label="total",
        )
        bars_ok = ax.bar(
            [i + bar_w / 2 for i in xi], mdf["success_rps"], width=bar_w,
            color="#55A868", label="successful",
        )
        for bar, val in list(zip(bars_total, mdf["rps"])) + list(zip(bars_ok, mdf["success_rps"])):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.2,
                f"{val:.1f}",
                ha="center", va="bottom", fontsize=8,
            )
        ax.set_xticks(list(xi))
        ax.set_xticklabels(x, fontsize=9)
        ax.legend(fontsize=9)
        ax.set_xlabel("concurrent users", fontsize=11)
        ax.set_ylabel("avg requests / second per operation", fontsize=11)
        ax.set_axisbelow(True)
        ax.grid(True, axis="y")
        ax.set_ylim(bottom=0)
        fig.tight_layout()
        save(fig, out / f"{adapter}_{mode}.png", show)


def fig_failures(df: pd.DataFrame, labels: dict, show: bool) -> None:
    out = subdir("failures")
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]

    for (adapter, mode), mdf in df.groupby(["adapter", "mode"]):
        lbl = run_label(labels, adapter, mode)
        users_sorted = sorted(mdf["users"].unique())
        x = [str(u) for u in users_sorted]
        ops = ops_present(mdf)

        fig, (ax_count, ax_pct) = plt.subplots(1, 2, figsize=(11, 4))
        fig.suptitle(f"{lbl}: Failures vs Concurrency", fontsize=13, fontweight="bold")

        for i, op in enumerate(ops):
            odf = mdf[mdf["op"] == op].sort_values("users")
            counts = [odf[odf["users"] == u]["failures"].values[0] if u in odf["users"].values else 0 for u in users_sorted]
            reqs = [odf[odf["users"] == u]["requests"].values[0] if u in odf["users"].values else 1 for u in users_sorted]
            pcts = [c / r * 100 if r > 0 else 0 for c, r in zip(counts, reqs)]
            col = colors[i % len(colors)]
            label = op.replace("_", " ")
            ax_count.plot(x, counts, marker="o", linewidth=2, color=col, label=label)
            ax_pct.plot(x, pcts, marker="o", linewidth=2, color=col, label=label)

        for ax, ylabel, title in [
            (ax_count, "total failures", "Failure Count"),
            (ax_pct, "failure rate (%)", "Failure Rate"),
        ]:
            ax.set_xlabel("concurrent users", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_title(title)
            ax.legend(fontsize=8)
            ax.grid(True)
            ax.set_ylim(bottom=0)

        fig.tight_layout()
        save(fig, out / f"{adapter}_{mode}.png", show)


def fig_latency_over_time(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    if not history:
        return
    out = subdir("latency_over_time")
    for run_key, hdf_full in sorted(history.items()):
        hdf = hdf_full[hdf_full["Name"] == "Aggregated"]
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        lbl = run_label(labels, m.group(1), m.group(2)) if m else run_key
        users_str = f"{m.group(3)} Users" if m else run_key

        fig, (ax_lat, ax_rps) = plt.subplots(1, 2, figsize=(11, 4))
        fig.suptitle(
            f"{lbl}: Latency and Throughput Over Time ({users_str})",
            fontsize=13,
            fontweight="bold",
        )

        ax_lat.plot(
            hdf["elapsed_s"],
            hdf["50%"],
            label="p50",
            linewidth=2,
            color=PCTILE_COLORS["p50"],
        )
        ax_lat.plot(
            hdf["elapsed_s"],
            hdf["95%"],
            label="p95",
            linewidth=2,
            color=PCTILE_COLORS["p95"],
        )
        ax_lat.set_xlabel("elapsed (s)", fontsize=11)
        ax_lat.set_ylabel("latency (ms)", fontsize=11)
        ax_lat.set_title("Latency Over Time")
        ax_lat.legend(fontsize=10)
        ax_lat.grid(True)
        ax_lat.set_ylim(bottom=0)

        ax_rps.plot(hdf["elapsed_s"], hdf["Requests/s"], linewidth=2, color="#55A868")
        ax_rps.set_xlabel("elapsed (s)", fontsize=11)
        ax_rps.set_ylabel("requests / second", fontsize=11)
        ax_rps.set_title("Throughput Over Time")
        ax_rps.grid(True)
        ax_rps.set_ylim(bottom=0)

        fig.tight_layout()
        save(fig, out / f"{run_key}.png", show)


def fig_user_count(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    if not history:
        return
    out = subdir("latency_over_time")
    for run_key, hdf_full in sorted(history.items()):
        hdf = hdf_full[hdf_full["Name"] == "Aggregated"]
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        lbl = run_label(labels, m.group(1), m.group(2)) if m else run_key
        users_str = f"{m.group(3)} Users" if m else run_key

        fig, ax = plt.subplots(figsize=(7, 4))
        fig.suptitle(
            f"{lbl}: User Count Over Time ({users_str})", fontsize=13, fontweight="bold"
        )

        ax.plot(hdf["elapsed_s"], hdf["User Count"], linewidth=2, color="#8172B2")
        ax.set_xlabel("elapsed (s)", fontsize=11)
        ax.set_ylabel("active users", fontsize=11)
        ax.grid(True)
        ax.set_ylim(bottom=0)
        fig.tight_layout()
        save(fig, out / f"{run_key}_users.png", show)


def fig_latency_per_op(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    """One image per (service, user count), 5 subplots (one per op), p50+p95 lines."""
    if not history:
        return
    out = subdir("latency_per_op")

    for run_key, hdf in sorted(history.items()):
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        if not m:
            continue
        lbl = run_label(labels, m.group(1), m.group(2))
        users = m.group(3)

        ops_in_run = [op for op in OP_ORDER if op in hdf["Name"].values]
        if not ops_in_run:
            continue

        ncols = 3
        nrows = -(-len(ops_in_run) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows))
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        fig.suptitle(
            f"{lbl}: Latency Over Time ({users} Users)",
            fontsize=13, fontweight="bold",
        )

        for i, op in enumerate(ops_in_run):
            ax = axes_flat[i]
            odf = hdf[hdf["Name"] == op]
            ax.plot(odf["elapsed_s"], odf["50%"], linewidth=2,
                    color=PCTILE_COLORS["p50"])
            ax.set_title(op.replace("_", " ").title(), fontsize=10)
            ax.set_xlabel("elapsed (s)", fontsize=9)
            ax.set_ylabel("p50 latency (ms)", fontsize=9)
            ax.grid(True)
            ax.set_ylim(bottom=0)

        for j in range(len(ops_in_run), len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.tight_layout()
        save(fig, out / f"{run_key}.png", show)


def fig_failures_per_op(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    """One image per (service, user count), 5 subplots (one per op), failure rate line."""
    if not history:
        return
    out = subdir("failures_per_op")

    for run_key, hdf in sorted(history.items()):
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        if not m:
            continue
        lbl = run_label(labels, m.group(1), m.group(2))
        users = m.group(3)

        ops_in_run = [op for op in OP_ORDER if op in hdf["Name"].values]
        if not ops_in_run:
            continue

        ncols = 3
        nrows = -(-len(ops_in_run) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows))
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        fig.suptitle(
            f"{lbl}: Failure Rate Over Time ({users} Users)",
            fontsize=13, fontweight="bold",
        )

        for i, op in enumerate(ops_in_run):
            ax = axes_flat[i]
            odf = hdf[hdf["Name"] == op].copy()
            odf["failure_pct"] = (
                odf["Failures/s"] / odf["Requests/s"].replace(0, float("nan")) * 100
            ).fillna(0)
            ax.plot(odf["elapsed_s"], odf["failure_pct"], linewidth=2, color="#F44336")
            ax.set_title(op.replace("_", " ").title(), fontsize=10)
            ax.set_xlabel("elapsed (s)", fontsize=9)
            ax.set_ylabel("failure rate (%)", fontsize=9)
            ax.grid(True)
            ax.set_ylim(bottom=0, top=100)

        for j in range(len(ops_in_run), len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.tight_layout()
        save(fig, out / f"{run_key}.png", show)


def fig_user_count_combined(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    if not history:
        return
    out = subdir("latency_over_time")
    run_keys = sorted(history.keys())
    ncols = min(3, len(run_keys))
    nrows = -(-len(run_keys) // ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.5 * nrows))
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
    fig.suptitle("User Count Over Time", fontsize=13, fontweight="bold")

    for i, run_key in enumerate(run_keys):
        hdf = history[run_key][history[run_key]["Name"] == "Aggregated"]
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        lbl = run_label(labels, m.group(1), m.group(2)) if m else run_key
        users_str = f"{m.group(3)} Users" if m else run_key
        ax = axes_flat[i]
        ax.plot(hdf["elapsed_s"], hdf["User Count"], linewidth=2, color="#8172B2")
        ax.set_title(f"{lbl} ({users_str})", fontsize=9)
        ax.set_xlabel("elapsed (s)", fontsize=9)
        ax.set_ylabel("users", fontsize=9)
        ax.grid(True)
        ax.set_ylim(bottom=0)

    for j in range(len(run_keys), len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.tight_layout()
    save(fig, out / "user_count_combined.png", show)


def fig_latency_over_time_per_op(
    history: "dict[str, pd.DataFrame]", labels: dict, show: bool
) -> None:
    if not history:
        return
    out = subdir("latency_over_time")
    ops = OP_ORDER

    for run_key, hdf_full in sorted(history.items()):
        m = re.match(r"(.+)_(direct|http)_(\d+)u$", run_key)
        lbl = run_label(labels, m.group(1), m.group(2)) if m else run_key
        users_str = f"{m.group(3)} Users" if m else run_key

        ops_in_run = [op for op in ops if op in hdf_full["Name"].values]
        if not ops_in_run:
            continue

        ncols = 3
        nrows = -(-len(ops_in_run) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows))
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        fig.suptitle(
            f"{lbl}: Latency Over Time by Operation ({users_str})",
            fontsize=13, fontweight="bold",
        )

        for i, op in enumerate(ops_in_run):
            odf = hdf_full[hdf_full["Name"] == op]
            ax = axes_flat[i]
            ax.plot(odf["elapsed_s"], odf["50%"], label="p50", linewidth=2,
                    color=PCTILE_COLORS["p50"])
            ax.plot(odf["elapsed_s"], odf["95%"], label="p95", linewidth=2,
                    color=PCTILE_COLORS["p95"])
            ax.set_title(op.replace("_", " ").title(), fontsize=10)
            ax.set_xlabel("elapsed (s)", fontsize=9)
            ax.set_ylabel("latency (ms)", fontsize=9)
            ax.legend(fontsize=8)
            ax.grid(True)
            ax.set_ylim(bottom=0)

        for j in range(len(ops_in_run), len(axes_flat)):
            axes_flat[j].set_visible(False)

        fig.tight_layout()
        save(fig, out / f"{run_key}_per_op.png", show)


def fig_cold_start(show: bool) -> None:
    csv_path = RESULTS_DIR / "cold_start.csv"
    if not csv_path.exists():
        return
    out = subdir("cold_start")
    df = pd.read_csv(csv_path).dropna(subset=["cold_ms"])
    if df.empty:
        return

    if "service" not in df.columns:
        df["service"] = "postgres"

    agg = df.groupby("service")["cold_ms"].mean().reset_index()
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860"]

    fig, ax = plt.subplots(figsize=(max(5, len(agg) * 1.5), 4))
    fig.suptitle("Cold Start Latency by Service", fontsize=13, fontweight="bold")

    bars = ax.bar(agg["service"], agg["cold_ms"], color=colors[:len(agg)], width=0.5)
    for bar, val in zip(bars, agg["cold_ms"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
            f"{val:.0f} ms", ha="center", va="bottom", fontsize=9,
        )

    ax.set_ylabel("avg cold start (ms)", fontsize=11)
    ax.set_axisbelow(True)
    ax.grid(True, axis="y")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    save(fig, out / "cold_start.png", show)


def fig_mode_comparison(df: pd.DataFrame, labels: dict, show: bool) -> None:
    adapters_with_both = [
        a
        for a in df["adapter"].unique()
        if {"direct", "http"} <= set(df[df["adapter"] == a]["mode"].unique())
    ]
    if not adapters_with_both:
        return
    out = subdir("mode_comparison")

    for adapter in adapters_with_both:
        adf = df[df["adapter"] == adapter]
        ops = ops_present(adf)  # pyright: ignore[reportArgumentType]
        x = range(len(ops))
        bar_w = 0.35
        direct_lbl = run_label(labels, adapter, "direct")
        http_lbl = run_label(labels, adapter, "http")

        for users in sorted(adf["users"].unique()):
            udf = adf[adf["users"] == users]

            def p95_vals(mode):
                mdf = udf[udf["mode"] == mode]
                return [
                    mdf[mdf["op"] == op]["p95"].values[0]
                    if op in mdf["op"].values
                    else 0
                    for op in ops
                ]

            direct_vals = p95_vals("direct")
            http_vals = p95_vals("http")

            fig, ax = plt.subplots(figsize=(9, 4))
            fig.suptitle(
                f"P95 Latency Comparison: {users} Users", fontsize=13, fontweight="bold"
            )

            b1 = ax.bar(
                [xi - bar_w / 2 for xi in x],
                direct_vals,
                width=bar_w,
                label=direct_lbl,
                color="#4C72B0",
            )
            b2 = ax.bar(
                [xi + bar_w / 2 for xi in x],
                http_vals,
                width=bar_w,
                label=http_lbl,
                color="#DD8452",
            )

            for bar, val in list(zip(b1, direct_vals)) + list(zip(b2, http_vals)):
                if val > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 1,
                        f"{val:.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

            ax.set_xticks(list(x))
            ax.set_xticklabels([op.replace("_", "\n") for op in ops], fontsize=9)
            ax.set_ylabel("p95 latency (ms)", fontsize=11)
            ax.legend(fontsize=10)
            ax.set_axisbelow(True)
            ax.grid(True, axis="y")
            ax.set_ylim(bottom=0)
            fig.tight_layout()
            save(fig, out / f"{adapter}_{users}u.png", show)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-show", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    show = not args.no_show

    df = load_stats()
    if df.empty:
        rich.print(f"[red]No results found in {RESULTS_DIR}/.[/red]")
        return

    labels = load_labels()
    history = load_history()

    runs = df.sort_values(by=["adapter", "mode", "users"])[
        ["adapter", "mode", "users"]
    ].drop_duplicates()
    rich.print(f"\n[bold]Loaded {len(df)} rows from {len(runs)} runs:[/bold]")
    for _, r in runs.iterrows():
        lbl = run_label(labels, r["adapter"], r["mode"])  # pyright: ignore[reportArgumentType]
        rich.print(f"  {lbl}  ({r['users']} users)")
    rich.print()

    for fn in [
        lambda: fig_latency_vs_concurrency(df, labels, show),
        lambda: fig_latency_avg(df, labels, show),
        lambda: fig_latency_bars(df, labels, show),
        lambda: fig_cold_start(show),
        lambda: fig_latency_per_op(history, labels, show),
        lambda: fig_failures_per_op(history, labels, show),
        lambda: fig_throughput(df, labels, show),
        lambda: fig_failures(df, labels, show),
        lambda: fig_latency_over_time(history, labels, show),
        lambda: fig_user_count_combined(history, labels, show),
        lambda: fig_mode_comparison(df, labels, show),
    ]:
        try:
            fn()
        except Exception as e:
            rich.print(f"  [yellow]warning: chart skipped — {e}[/yellow]")

    rich.print(f"\n[green]Done.[/green] Figures in [bold]{FIGURES_DIR}/[/bold]")


if __name__ == "__main__":
    main()
