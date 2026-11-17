"""Charts for the report. Every function draws one figure and optionally saves it."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config

INK = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BLUE = "#2563EB"
ORANGE = "#EA580C"
RED = "#DC2626"
GREEN = "#16A34A"
LIGHT = "#CBD5E1"


def set_style() -> None:
    """Apply the shared chart style."""
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": GRID, "axes.labelcolor": INK, "axes.titlecolor": INK,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 10, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 10,
        "legend.frameon": False,
    })


def _finish(fig: plt.Figure, path: Path | None, subtitle: str | None = None) -> plt.Figure:
    if subtitle:
        fig.text(0.01, -0.02, subtitle, ha="left", va="top", fontsize=8.5, color=MUTED)
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path)
    return fig


def coverage_heatmap(table: pd.DataFrame, title: str, path: Path | None = None) -> plt.Figure:
    """City x year coverage heatmap (share of days with data)."""
    table = table.loc[table.mean(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(8, 8))
    sns.heatmap(table * 100, ax=ax, cmap="Blues", vmin=0, vmax=100, annot=True, fmt=".0f",
                linewidths=0.5, linecolor="white", cbar_kws={"label": "% of days with data"},
                annot_kws={"fontsize": 8})
    ax.set(title=title, xlabel="", ylabel="")
    ax.grid(False)
    return _finish(fig, path)


def co_anomaly(df: pd.DataFrame, path: Path | None = None) -> plt.Figure:
    """Ahmedabad's weekly CO against the range seen in every other city (log scale)."""
    weekly = (df.set_index("Date").groupby("City")["CO"].resample("W").median()
              .unstack("City"))
    # Zero readings (sensor floor) cannot be drawn on a log scale, so treat them as missing.
    others = weekly.drop(columns="Ahmedabad").where(lambda w: w > 0)
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.fill_between(others.index, others.quantile(0.10, axis=1), others.quantile(0.90, axis=1),
                    color=LIGHT, alpha=0.7,
                    label=f"Other {others.shape[1]} cities (10th–90th percentile)")
    ax.plot(others.index, others.median(axis=1), color=MUTED, lw=1, label="Other cities (median)")
    ax.plot(weekly.index, weekly["Ahmedabad"], color=RED, lw=1.3, label="Ahmedabad")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 150)
    ax.set(title="Ahmedabad's CO readings are not plausible until April 2020",
           ylabel="Weekly median CO (mg/m³, log scale)")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
    return _finish(fig, path)


def change_overview(summaries: dict[str, dict], path: Path | None = None,
                    title: str = "Lockdown effect by pollutant") -> plt.Figure:
    """Simple vs adjusted change in the typical city, for each pollutant."""
    pollutants = list(summaries)
    x = np.arange(len(pollutants))
    raw = [summaries[p]["typical_raw_change"] * 100 for p in pollutants]
    adj = [summaries[p]["typical_adjusted_change"] * 100 for p in pollutants]
    lo = [summaries[p]["ci_low"] * 100 for p in pollutants]
    hi = [summaries[p]["ci_high"] * 100 for p in pollutants]

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(x - 0.2, raw, 0.38, color=LIGHT, label="Simple comparison (2020 vs 2019)")
    clear = [h < 0 or lo_ > 0 for lo_, h in zip(lo, hi, strict=True)]
    ax.bar(x + 0.2, adj, 0.38,
           color=[(BLUE if a < 0 else ORANGE) if c else MUTED
                  for a, c in zip(adj, clear, strict=True)],
           label="Lockdown effect (adjusted for pre-lockdown trend)")
    ax.errorbar(x + 0.2, adj, yerr=[np.subtract(adj, lo), np.subtract(hi, adj)],
                fmt="none", ecolor=INK, capsize=4, lw=1)
    for xi, a, low, high in zip(x, adj, lo, hi, strict=True):
        # Label beyond the end of the error bar, so it never overlaps the bar or whisker.
        anchor, offset = (low, -15) if a < 0 else (high, 5)
        ax.annotate(f"{a:+.0f}%", (xi + 0.2, anchor), xytext=(0, offset),
                    textcoords="offset points", ha="center", fontsize=9.5, color=INK,
                    fontweight="bold")
    ax.margins(y=0.12)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x, [f"{p}\n({summaries[p]['n_cities']} cities)" for p in pollutants])
    ax.set(title=title, ylabel="Change in the typical city (%)")
    ax.legend(loc="upper left", fontsize=9)
    return _finish(fig, path, "Typical city = geometric mean across cities. Error bars: 95% "
                              "interval from resampling cities. Grey: no clear change.")


def city_effects(effects: pd.DataFrame, pollutant: str, path: Path | None = None) -> plt.Figure:
    """Dot-and-whisker chart of the adjusted lockdown effect per city (stable baselines only)."""
    excluded = effects.loc[~effects["stable_baseline"], "City"].tolist()
    e = effects[effects["stable_baseline"]].sort_values("adjusted_change", ascending=False)
    y = np.arange(len(e))
    colors = [BLUE if h < 0 else (ORANGE if lo > 0 else MUTED)
              for lo, h in zip(e["ci_low"], e["ci_high"], strict=True)]
    fig, ax = plt.subplots(figsize=(7.5, 0.36 * len(e) + 1.4))
    ax.hlines(y, e["ci_low"] * 100, e["ci_high"] * 100, color=colors, lw=2, alpha=0.6)
    ax.scatter(e["adjusted_change"] * 100, y, color=colors, s=36, zorder=3)
    ax.scatter(e["raw_change"] * 100, y, facecolor="none", edgecolor=MUTED, s=26, zorder=2,
               label="Simple 2020 vs 2019 comparison")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y, e["City"])
    ax.set(title=f"{pollutant}: lockdown effect by city",
           xlabel="Change in median concentration, adjusted for pre-lockdown trend (%)")
    ax.legend(loc="upper right", fontsize=8.5)
    note =("Filled dot: adjusted estimate. Line: 95% bootstrap interval. Blue: clear decrease. "
            "Orange: clear increase. Grey: not distinguishable from no change.")
    if excluded:
        note += f"\nExcluded (unstable 2019 baseline): {', '.join(excluded)}."
    return _finish(fig, path, note)


def city_timeline(series: pd.DataFrame, city: str, pollutant: str,
                  path: Path | None = None) -> plt.Figure:
    """2019 vs 2020, aligned by day of year, with study windows shaded."""
    ref = pd.Timestamp("2020-01-01")
    idx = [ref + pd.Timedelta(days=d - 1) for d in series.index]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for (name, (start, end)), shade in zip(
            {"Pre-lockdown window": config.PRE_LOCKDOWN,
             "Lockdown (phases 1–2)": config.LOCKDOWN}.items(), ["#F1F5F9", "#DBEAFE"],
            strict=True):
        ax.axvspan(pd.Timestamp(f"2020-{start}"), pd.Timestamp(f"2020-{end}"),
                   color=shade, zorder=0, label=name)
    ax.plot(idx, series[config.BASELINE_YEAR], color=MUTED, lw=1.4, label=str(config.BASELINE_YEAR))
    ax.plot(idx, series[config.STUDY_YEAR], color=BLUE, lw=1.8, label=str(config.STUDY_YEAR))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set(title=f"{city}: {pollutant}, 2020 vs 2019 (7-day average)",
           ylabel=f"{pollutant} ({config.UNITS.get(pollutant, '')})")
    ax.legend(loc="upper right", ncol=2, fontsize=9)
    return _finish(fig, path)


def diwali_profiles(groups: dict[str, pd.DataFrame], path: Path | None = None) -> plt.Figure:
    """Ratio to local baseline by day around Diwali, one panel per city group."""
    fig, axes = plt.subplots(1, len(groups), figsize=(5.6 * len(groups), 4.2), sharey=True)
    colors = [RED, BLUE, ORANGE, GREEN][: len(groups)]
    for ax, (label, prof), color in zip(np.atleast_1d(axes), groups.items(), colors, strict=True):
        for city in prof.columns:
            ax.plot(prof.index, prof[city], color=color, alpha=0.22, lw=1)
        typical = prof.median(axis=1)
        ax.plot(prof.index, typical, color=color, lw=2.6, label="Median city")
        ax.annotate(f"peak ×{typical.max():.1f} on day {int(typical.idxmax()):+d}",
                    (typical.idxmax(), typical.max()), xytext=(8, 4), textcoords="offset points",
                    fontsize=9, color=INK, fontweight="bold")
        ax.axvline(0, color=INK, lw=0.8, ls="--")
        ax.axhline(1, color=MUTED, lw=0.8)
        ax.set(title=label, xlabel="Days relative to Diwali")
        ax.set_xticks(range(-7, 8))
    np.atleast_1d(axes)[0].set_ylabel("PM2.5 relative to local baseline (×)")
    np.atleast_1d(axes)[0].legend(loc="upper left")
    fig.suptitle("PM2.5 around Diwali, 2015–2019", x=0.01, ha="left", fontsize=14,
                 fontweight="bold", color=INK, y=1.03)
    return _finish(fig, path, "Baseline: mean of days −7…−3 and +4…+7, which cancels the "
                              "seasonal rise. Thin lines: individual cities.")


def monthly_heatmap(profile: pd.DataFrame, path: Path | None = None) -> plt.Figure:
    """City x month median PM2.5."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(profile) + 1.5))
    sns.heatmap(profile, ax=ax, cmap="YlOrRd", annot=True, fmt=".0f", linewidths=0.5,
                linecolor="white", cbar_kws={"label": "Median PM2.5 (µg/m³)"},
                annot_kws={"fontsize": 8}, xticklabels=months)
    ax.set(title="Winter is the pollution season, and North India is hit hardest",
           xlabel="", ylabel="")
    ax.grid(False)
    return _finish(fig, path, "Median daily PM2.5 per month, 2015–2020. India's 24-hour "
                              "PM2.5 standard is 60 µg/m³.")
