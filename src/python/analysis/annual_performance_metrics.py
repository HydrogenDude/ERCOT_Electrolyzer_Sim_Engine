#!/usr/bin/env python3
"""
electrolyzer_metrics_figure.py
──────────────────────────────
5-row single-column figure; each panel uses dual y-axes to overlay
the two paired metrics.  Ticks: exactly 4 per axis, computed to be
nicely rounded with the outer ticks strictly outside the data range.
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

# ── Style ─────────────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    'font.size':        14,
    'axes.labelsize':   14,
    'xtick.labelsize':  14,
    'ytick.labelsize':  14,
    'axes.spines.top':  True,
    'axes.grid':        False,
    'lines.linewidth':  1.8,
    'lines.markersize': 5.5,
})

# ── Data ──────────────────────────────────────────────────────────────────────
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

PAIRS = [
    (
        'H$_2$ produced\n(t yr$^{-1}$)',
        [0.9, 1.5, 1.4, 1.6, 1.8, 2.3],
        '#1A6FA3',
        'Energy used\n(MWh yr$^{-1}$)',
        [91.3, 154.2, 139.2, 154.8, 177.3, 226.5],
        '#5BAEE0',
    ),
    (
        'Capacity factor\n(%)',
        [13.9, 23.5, 21.2, 23.6, 27.0, 34.5],
        '#2A9B5B',
        'Utilization\n(%)',
        [15.5, 25.1, 22.1, 25.0, 28.3, 36.2],
        '#56C482',
    ),
    (
        'CO$_2$ emitted\n(t yr$^{-1}$)',
        [25.5, 41.8, 35.8, 36.5, 40.4, 51.9],
        '#CC3333',
        'CO$_2$ intensity\n(kg kg$^{-1}$ H$_2$)',
        [28.5, 27.1, 25.4, 23.4, 22.6, 22.7],
        '#8C1C1C',
    ),
    (
        'Electricity cost\n(kUSD yr$^{-1}$)',
        [v / 1000 for v in [1041, 2274, 2985, 2126, 2061, 4136]],
        '#6E2B9A',
        'LCOE\n(USD kg$^{-1}$ H$_2$)',
        [1.2, 1.5, 2.1, 1.4, 1.2, 1.8],
        '#A860CF',
    ),
    (
        'Annual startups',
        [66, 85, 93, 74, 108, 178],
        '#D4691A',
        'H$_2$ per startup\n(kg)',
        [13.6, 18.1, 15.3, 20.9, 16.5, 12.8],
        '#9A3E00',
    ),
]


# ── Tick helpers ──────────────────────────────────────────────────────────────
def make_ticks(vmin, vmax, n=4):
    """
    Return n evenly-spaced, nicely rounded ticks where
    ticks[0] < vmin  and  ticks[-1] > vmax.

    Strategy: try increasing step sizes (nice multiples of the
    appropriate power of 10) until a starting point exists that
    places the first tick strictly below vmin and the last tick
    strictly above vmax.
    """
    span  = vmax - vmin
    mag   = 10 ** np.floor(np.log10(span / (n - 1)))

    # Candidate nice multipliers tried in ascending order.
    # 15 is included to avoid overly wide ranges on ~20-unit spans.
    nice_factors = [1, 2, 2.5, 5, 10, 15, 20, 25, 50]

    for factor in nice_factors:
        step    = factor * mag
        k_base  = int(np.floor(vmin / step))
        # Try a handful of starting-point offsets
        for k_offset in [0, -1, 1, -2, 2, -3]:
            t0    = (k_base + k_offset) * step
            if t0 >= vmin - 1e-10:      # must be strictly left of data
                continue
            ticks = np.array([t0 + i * step for i in range(n)])
            if ticks[-1] > vmax + 1e-10:  # last tick strictly right of data
                return ticks

    # Fallback (should be unreachable for well-formed data)
    step = 50 * mag
    t0   = (int(np.floor(vmin / step)) - 1) * step
    return np.array([t0 + i * step for i in range(n)])


def tick_labels(ticks):
    """
    Format a tick array as strings.
    Integer ticks → plain integers.
    One-decimal ticks → one decimal place.
    Otherwise → two decimal places.
    """
    if np.allclose(ticks, np.round(ticks, 0), atol=1e-9):
        return [str(int(round(v))) for v in ticks]
    elif np.allclose(ticks, np.round(ticks, 1), atol=1e-9):
        return [f'{v:.1f}' for v in ticks]
    else:
        return [f'{v:.2f}' for v in ticks]


# ── Figure ────────────────────────────────────────────────────────────────────
N   = len(PAIRS)
fig, axes = plt.subplots(N, 1, figsize=(7, 10))
fig.subplots_adjust(top=0.97, hspace=0.1, left=0.15, right=0.82)

xs = np.array(YEARS)

for idx, (ll, lv, lc, rl, rv, rc) in enumerate(PAIRS):
    ax_l = axes[idx]
    ax_r = ax_l.twinx()

    lys = np.array(lv)
    rys = np.array(rv)

    l_legend = ll.split('\n')[0]
    r_legend = rl.split('\n')[0]

    # ── Lines ─────────────────────────────────────────────────────────────────
    ax_l.plot(xs, lys, color=lc, marker='o',  zorder=3, clip_on=False,
              label=l_legend)
    ax_r.plot(xs, rys, color=rc, marker='s', linestyle='--',
              linewidth=1.6, zorder=3, clip_on=False, label=r_legend)

    # ── Axis labels ───────────────────────────────────────────────────────────
    ax_l.yaxis.set_label_position('left')
    ax_r.yaxis.set_label_position('right')
    ax_l.set_ylabel(ll, labelpad=20, rotation=90, va='center')
    ax_r.set_ylabel(rl, labelpad=20, rotation=90, va='center')

    # ── Manual ticks ──────────────────────────────────────────────────────────
    lticks = make_ticks(min(lv), max(lv))
    rticks = make_ticks(min(rv), max(rv))

    ax_l.set_yticks(lticks)
    ax_r.set_yticks(rticks)
    ax_l.set_yticklabels(tick_labels(lticks))
    ax_r.set_yticklabels(tick_labels(rticks))

    # Extend limits slightly beyond the outer ticks so they don't sit
    # flush against the spine.  Adjust PAD to taste (fraction of tick span).
    PAD = 0.06
    ax_l.set_ylim(lticks[0] - PAD * (lticks[-1] - lticks[0]),
                  lticks[-1] + PAD * (lticks[-1] - lticks[0]))
    ax_r.set_ylim(rticks[0] - PAD * (rticks[-1] - rticks[0]),
                  rticks[-1] + PAD * (rticks[-1] - rticks[0]))

    # ── Tick appearance ───────────────────────────────────────────────────────
    for ax in (ax_l, ax_r):
        ax.tick_params(axis='y', colors='black', direction='out', length=4)

    # ── X-axis ────────────────────────────────────────────────────────────────
    ax_l.set_xticks(xs)
    ax_l.set_xlim(YEARS[0] - 0.35, YEARS[-1] + 0.35)
    if idx == N - 1:
        ax_l.set_xticklabels([str(y) for y in YEARS])
    else:
        ax_l.set_xticklabels([])


# ── Figure-level line-style legend ───────────────────────────────────────────
from matplotlib.lines import Line2D

legend_handles = [
    Line2D([0], [0], color='black', linestyle='-',  linewidth=1.8,
           label='Left axis'),
    Line2D([0], [0], color='black', linestyle='--', linewidth=1.6,
           label='Right axis'),
]
fig.legend(handles=legend_handles, loc='lower center', ncol=2,
           fontsize=12, frameon=True, edgecolor='black',
           fancybox=False, bbox_to_anchor=(0.5, 0.01))

plt.show()