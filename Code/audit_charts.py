"""Static charts for the financial audit PDF (matplotlib -> PNG).

Colour roles follow one rule: blue is the data, red only means "over budget"
(always paired with a text label), grays are chrome.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

BLUE = "#2a78d6"        # series slot 1
BLUE_LIGHT = "#9ec5f4"  # same ramp, lighter step: values dated after the report date
CRITICAL = "#d03b3b"    # status: over budget
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#ffffff"

DPI = 220
WIDTH_IN = 7.0          # matches the PDF content width (~178 mm)

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 8.5,
    "text.color": INK,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": SECONDARY,
    "xtick.color": SECONDARY,
    "ytick.color": SECONDARY,
    "axes.titlesize": 9.5,
    "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round",
})

LABEL_BG = dict(boxstyle="square,pad=0.15", facecolor=SURFACE, edgecolor="none")

K = FuncFormatter(lambda v, _: f"${v / 1000:,.0f}K" if v else "$0")


def _frame(ax, grid_axis="y"):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, pad=4)


def _save(fig, path):
    fig.savefig(path, dpi=DPI, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return path


def _past_future_line(ax, x, y, cut):
    """Solid line to the report date; dashed with hollow markers after it."""
    ax.plot(x[:cut + 1], y[:cut + 1], color=BLUE, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
    if cut < len(x) - 1:
        ax.plot(x[cut:], y[cut:], color=BLUE, linewidth=2, linestyle=(0, (3, 2)), zorder=2)
        ax.plot(x[cut + 1:], y[cut + 1:], linestyle="none", marker="o", markersize=5,
                markerfacecolor=SURFACE, markeredgecolor=BLUE, markeredgewidth=1.5, zorder=3)


def _future_handles():
    return [Line2D([], [], color=BLUE, linewidth=2, marker="o", markersize=5,
                   markeredgecolor=SURFACE, label="Actual spend"),
            Line2D([], [], color=BLUE, linewidth=2, linestyle=(0, (3, 2)), marker="o", markersize=5,
                   markerfacecolor=SURFACE, markeredgecolor=BLUE, label="Dated after report date")]


def _month_labels(months):
    import pandas as pd
    return [pd.Period(m).strftime("%b") for m in months]


def budget_utilisation(dept, threshold_pct, path):
    """Horizontal bars: spend as % of budget per department, 100% reference."""
    d = dept.assign(Used=dept["Actual"] / dept["Budget"] * 100).sort_values("Used")
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.45))
    colors = [CRITICAL if f else BLUE for f in d["Flagged"]]
    ax.barh(d["Department"], d["Used"], height=0.55, color=colors)
    ax.axvline(100, color=SECONDARY, linewidth=1)
    ax.text(100, len(d) - 0.35, " Budget (100%)", color=SECONDARY, va="bottom", ha="left", fontsize=8)
    for y, (used, flagged) in enumerate(zip(d["Used"], d["Flagged"])):
        label = f"{used:.0f}%" + (f"  over budget by {used - 100:.0f}%" if flagged else "")
        ax.text(used + 1.5, y, label, va="center", fontsize=8, color=INK,
                fontweight="bold" if flagged else "normal")
    ax.set_xlim(0, max(150, d["Used"].max() + 35))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _frame(ax, grid_axis="x")
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="y", labelcolor=INK)
    return _save(fig, path)


def monthly_spend_vs_budget(monthly, budget_total, as_of_month, path):
    """Columns: company spend per month against the combined monthly budget."""
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.0))
    labels = _month_labels(monthly.index)
    future = [m > as_of_month for m in monthly.index]
    ax.bar(labels, monthly.values, width=0.55,
           color=[BLUE_LIGHT if f else BLUE for f in future])
    ax.axhline(budget_total, color=SECONDARY, linewidth=1)
    ax.text(len(labels) - 0.5, budget_total, f"Combined monthly budget ${budget_total / 1000:,.0f}K",
            color=SECONDARY, fontsize=8, ha="right", va="bottom")
    first, last = monthly.iloc[0], monthly.iloc[-1]
    ax.text(0, first, f"${first / 1000:,.0f}K", ha="center", va="bottom", fontsize=8)
    ax.text(len(labels) - 1, last, f"${last / 1000:,.0f}K", ha="center", va="bottom", fontsize=8)
    if any(future):
        ax.legend(handles=[Patch(color=BLUE, label="To date"),
                           Patch(color=BLUE_LIGHT, label="Dated after report date")],
                  loc="upper left", frameon=False, fontsize=8, ncol=2, handlelength=1.2)
    ax.yaxis.set_major_formatter(K)
    ax.set_ylim(0, budget_total * 1.22)
    _frame(ax)
    return _save(fig, path)


def marketing_trend(mkt_var, as_of_month, path):
    """Line: Marketing actual spend per month vs its flat monthly budget."""
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.6))
    x = list(range(len(mkt_var)))
    labels = _month_labels(mkt_var["Month"])
    actual, budget = mkt_var["Actual_Spend"].values, mkt_var["Budget"].values
    cut = max(i for i, m in enumerate(mkt_var["Month"]) if m <= as_of_month)

    ax.fill_between(x, budget, actual, where=actual > budget, interpolate=True,
                    color=CRITICAL, alpha=0.10, linewidth=0)
    ax.plot(x, budget, color=MUTED, linewidth=1.5)
    _past_future_line(ax, x, actual, cut)
    ax.annotate(f"${actual[-1] / 1000:,.0f}K", (x[-1], actual[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8)
    ax.text(x[-1] + 0.2, budget[-1], f"Budget ${budget[-1] / 1000:,.0f}K", fontsize=8,
            color=SECONDARY, va="center")
    mid = 6  # label sits inside the shaded band, below the line
    ax.text(x[mid], budget[mid] + (actual[mid] - budget[mid]) * 0.35, "Over budget",
            fontsize=7.5, ha="center", va="center", color=INK)
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(K)
    ax.set_ylim(0, actual.max() * 1.15)
    ax.set_xlim(-0.3, len(x) + 0.6)
    handles = _future_handles() if cut < len(x) - 1 else _future_handles()[:1]
    handles.append(Line2D([], [], color=MUTED, linewidth=1.5, label="Monthly budget"))
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=8, ncol=3, handlelength=2.2)
    _frame(ax)
    return _save(fig, path)


def roas_by_channel(channels, blended, path):
    """Horizontal bars: ROAS per marketing channel, blended ROAS reference."""
    c = channels.sort_values("ROAS")
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.5))
    ax.barh(c["Vendor"], c["ROAS"], height=0.55, color=BLUE)
    ax.axvline(blended, color=SECONDARY, linewidth=1, zorder=1)
    ax.text(blended, len(c) - 0.35, f" Blended {blended:.1f}x", color=SECONDARY, fontsize=8, va="bottom")
    for y, (roas, spend) in enumerate(zip(c["ROAS"], c["Spend"])):
        ax.text(roas + 0.12, y, f"{roas:.1f}x  (${spend / 1000:,.0f}K spent)", va="center", fontsize=8,
                bbox=LABEL_BG, zorder=4)
    ax.set_xlim(0, c["ROAS"].max() * 1.35)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}x"))
    _frame(ax, grid_axis="x")
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="y", labelcolor=INK)
    return _save(fig, path)


def vendor_trend(monthly, vendor, as_of_month, path):
    """Line: one vendor's spend per month."""
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.3))
    x = list(range(len(monthly)))
    y = monthly.values
    cut = max(i for i, m in enumerate(monthly.index) if m <= as_of_month)
    ax.fill_between(x, 0, y, color=BLUE, alpha=0.08, linewidth=0)
    _past_future_line(ax, x, y, cut)
    if cut < len(x) - 1:
        ax.legend(handles=_future_handles(), loc="upper left", frameon=False, fontsize=8, ncol=2,
                  handlelength=2.2)
    ax.annotate(f"${y[0] / 1000:,.0f}K", (0, y[0]), xytext=(0, 7), textcoords="offset points",
                ha="center", fontsize=8)
    ax.annotate(f"${y[-1] / 1000:,.0f}K", (x[-1], y[-1]), xytext=(0, 7), textcoords="offset points",
                ha="center", fontsize=8)
    ax.set_xticks(x, _month_labels(monthly.index))
    ax.yaxis.set_major_formatter(K)
    ax.set_ylim(0, y.max() * 1.35)
    ax.set_xlim(-0.4, len(x) - 0.6)
    _frame(ax)
    return _save(fig, path)
