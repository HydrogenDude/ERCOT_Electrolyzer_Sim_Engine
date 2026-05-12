import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog
from scipy.spatial import ConvexHull

# =====================================================
# USER CONFIGURATION
# =====================================================
P_LOW  = 0
#P_HIGH = 90.5
P_HIGH = 88.2

REGION_MODE = True
REGION_PCT = (0, 88.2)
REGION_ALPHA = 0.1

PLOT_CONFIGS = [
    {"x": "h2",   "y": "co2",  "title": "H₂ vs CO₂"},
    {"x": "cost", "y": "h2",   "title": "Cost vs H₂"},
    {"x": "cost", "y": "co2",  "title": "Cost vs CO₂"},
]

AXIS_LABELS = {
    "h2": "Total H$_2$ produced (kg)",
    "co2": "Total CO$_2$ emitted (kg)",
    "cost": "Electricity cost (USD)",
    "startups": "Electrolyzer startups",
}

GROUP_FILTER = {
    "DonOff": {"off"},
    "year": {2020, 2021, 2022, 2023, 2024, 2025},
    "S": {20, 69, 26},
}

# Unique marker per dataset (ID1 only)
ID1_MARKERS = ["X", "D", "P", "^", "v", "s", "*", "<", ">", "h"]

# =====================================================
# FILE SELECTION
# =====================================================
def select_h5_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    files = filedialog.askopenfilenames(
        title="Select HDF5 result files",
        filetypes=[("HDF5 files", "*.h5")]
    )
    root.destroy()
    return [Path(f) for f in files]

h5_files = select_h5_files()
if not h5_files:
    raise RuntimeError("No files selected.")

# =====================================================
# FILENAME PARSING
# =====================================================
pattern = re.compile(
    r"N(?P<N>\d+)_S(?P<S>\d+)_D(?P<D>on|off)_(?P<year>\d{4})",
    re.IGNORECASE,
)

def dataset_selected(data, filt):
    for k, allowed in filt.items():
        if data.get(k) not in allowed:
            return False
    return True

# =====================================================
# LOAD DATASETS
# =====================================================
used_axes = {cfg["x"] for cfg in PLOT_CONFIGS} | {cfg["y"] for cfg in PLOT_CONFIGS}

datasets = []
all_vals = {k: [] for k in used_axes}
all_startups = []

for fpath in h5_files:
    meta = {"DonOff": None, "year": None, "S": None}
    m = pattern.search(fpath.stem)
    if m:
        gd = m.groupdict()
        meta.update(
            DonOff=gd["D"].lower(),
            year=int(gd["year"]),
            S=int(gd["S"]),
        )

    if not dataset_selected(meta, GROUP_FILTER):
        continue

    with h5py.File(fpath, "r") as f:
        data = dict(meta)
        data["label"] = fpath.stem
        data["h2"] = f["/totals/total_h2_kg"][:].ravel()
        data["co2"] = f["/totals/total_co2_kg"][:].ravel()
        data["cost"] = f["/totals/total_cost"][:].ravel()
        data["startups"] = f["/state/startups"][:].ravel()

    datasets.append(data)
    for k in used_axes:
        all_vals[k].append(data[k])
    all_startups.append(data["startups"])

if not datasets:
    raise RuntimeError("No datasets passed filters.")

# =====================================================
# COLOR NORMALIZATION (POINTS)
# =====================================================
norm = Normalize(
    vmin=np.percentile(np.concatenate(all_startups), 0),
    vmax=np.percentile(np.concatenate(all_startups), 99),
)
cmap = cm.jet

# =====================================================
# DATASET COLORS (REGIONS)
# =====================================================
dataset_cmap = plt.get_cmap("tab10")
dataset_colors = {
    i: dataset_cmap(i % dataset_cmap.N)
    for i in range(len(datasets))
}

# =====================================================
# AXIS LIMITS
# =====================================================
axis_limits = {
    k: np.percentile(np.concatenate(v), [P_LOW, P_HIGH])
    for k, v in all_vals.items()
}

# =====================================================
# 2D PLOT FUNCTION
# =====================================================
def plot_2d(ax, x_key, y_key):
    x_lo, x_hi = axis_limits[x_key]
    y_lo, y_hi = axis_limits[y_key]

    for i, data in enumerate(datasets):
        x = data[x_key]
        y = data[y_key]
        startups = data["startups"]

        marker = ID1_MARKERS[i % len(ID1_MARKERS)]

        # ---- ID 1 ----
        ax.scatter(
            x[0], y[0],
            c=[startups[0]],
            cmap=cmap,
            norm=norm,
            marker=marker,
            s=140,
            edgecolors="black",
            linewidths=2,
            zorder=100,
        )

        if REGION_MODE:
            x_p = np.percentile(x, REGION_PCT)
            y_p = np.percentile(y, REGION_PCT)

            mask = (
                (x >= x_p[0]) & (x <= x_p[1]) &
                (y >= y_p[0]) & (y <= y_p[1])
            )

            pts = np.column_stack([x[mask], y[mask]])
            if pts.shape[0] >= 3:
                hull = ConvexHull(pts)
                poly = Polygon(
                    pts[hull.vertices],
                    closed=True,
                    facecolor=dataset_colors[i],
                    edgecolor="none",
                    alpha=REGION_ALPHA,
                    zorder=1,
                )
                ax.add_patch(poly)

        else:
            inlier = (
                (x >= x_lo) & (x <= x_hi) &
                (y >= y_lo) & (y <= y_hi)
            )
            ax.scatter(
                x[inlier],
                y[inlier],
                c=startups[inlier],
                cmap=cmap,
                norm=norm,
                s=2,
                alpha=0.5,
                linewidth=0,
            )

    ax.set_xlabel(AXIS_LABELS[x_key])
    ax.set_ylabel(AXIS_LABELS[y_key])
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.grid(False)

# =====================================================
# FIGURE
# =====================================================
fig, axes = plt.subplots(
    1, len(PLOT_CONFIGS),
    figsize=(5 * len(PLOT_CONFIGS), 4),
    dpi=110,
    squeeze=False,
)

for ax, cfg in zip(axes[0], PLOT_CONFIGS):
    plot_2d(ax, cfg["x"], cfg["y"])
    ax.set_title(cfg.get("title", f"{cfg['x']} vs {cfg['y']}"))

# =====================================================
# LEGEND (ID1 ONLY — REGION MODE)
# =====================================================
if REGION_MODE:
    legend_handles = []
    for i, data in enumerate(datasets):
        marker = ID1_MARKERS[i % len(ID1_MARKERS)]
        handle = Line2D(
            [0], [0],
            marker=marker,
            linestyle="None",
            markerfacecolor="white",
            markeredgecolor="black",
            markeredgewidth=2,
            markersize=10,
            label=data["label"],
        )
        legend_handles.append(handle)

    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=min(len(legend_handles), 4),
        frameon=True,
        title="ID 1 Case (by dataset)",
    )

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.show()