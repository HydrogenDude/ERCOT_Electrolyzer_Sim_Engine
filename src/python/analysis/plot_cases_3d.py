import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog

# =====================================================
# Configuration
# =====================================================
P_LOW  = 0
P_HIGH = 88

GROUP_FILTER = {
    "DonOff": {"off"},
    "year": {2020, 2021, 2022, 2023, 2024, 2025},
    "S": {20, 69, 26},
}

# =====================================================
# Figure / style configuration
# =====================================================
FIG_CONFIG = {
    "figsize": (7, 5),
    "dpi": 120,

    "axes_pos": [0.10, 0.10, 0.68, 0.80],
    "cbar_pos": [0.82, 0.20, 0.02, 0.60],

    "label_fontsize": 12,
    "tick_fontsize": 10,
    "cbar_label_fontsize": 11,

    "n_ticks": 6,

    "marker_size": 4,
    "alpha": 0.7,
}

# =====================================================
# Predefined camera views
# =====================================================
VIEWS = {
    "iso":      dict(elev=20, azim=-20),
    "top":      dict(elev=90, azim=-90),
    "side_x":   dict(elev=0,  azim=0),
    "side_y":   dict(elev=0,  azim=90),
}

# =====================================================
# Select active view (ONLY THIS ONE WILL PLOT)
# =====================================================
ACTIVE_VIEW = "iso"   # <-- CHANGE THIS

if ACTIVE_VIEW not in VIEWS:
    raise ValueError(f"ACTIVE_VIEW '{ACTIVE_VIEW}' not found in VIEWS")

VIEW = VIEWS[ACTIVE_VIEW]

# =====================================================
# FILE SELECTION
# =====================================================
def select_h5_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_paths = filedialog.askopenfilenames(
        title="Select HDF5 result files",
        filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")]
    )

    root.destroy()
    return [Path(p) for p in file_paths]


h5_files = select_h5_files()

if not h5_files:
    raise RuntimeError("No files selected. Exiting.")

print("\n[INFO] Selected files:")
for f in h5_files:
    print(f"  {f}")

# =====================================================
# Filename parser
# =====================================================
pattern = re.compile(
    r"N(?P<N>\d+)_S(?P<S>\d+)_D(?P<D>on|off)_(?P<year>\d{4})",
    re.IGNORECASE,
)

# =====================================================
# Dataset selector
# =====================================================
def dataset_selected(data, group_filter):
    if "DonOff" in group_filter and data.get("DonOff") not in group_filter["DonOff"]:
        return False
    if "year" in group_filter and data.get("year") not in group_filter["year"]:
        return False
    if "S" in group_filter and data.get("S") not in group_filter["S"]:
        return False
    if "label" in group_filter and data.get("label") not in group_filter["label"]:
        return False
    return True

# =====================================================
# Load datasets
# =====================================================
datasets = []
all_startups, all_h2, all_co2, all_cost = [], [], [], []

for h5file in h5_files:
    meta = {}
    match = pattern.search(h5file.stem)

    if match:
        gd = match.groupdict()
        meta.update(
            DonOff=gd["D"].lower(),
            year=int(gd["year"]),
            S=int(gd["S"]),
        )
    else:
        meta.update(DonOff=None, year=None, S=None)

    data = {
        **meta,
        "label": h5file.stem,
        "filepath": str(h5file),
    }

    if not dataset_selected(data, GROUP_FILTER):
        continue

    with h5py.File(h5file, "r") as f:
        data["h2"] = f["/totals/total_h2_kg"][:].ravel()
        data["co2"] = f["/totals/total_co2_kg"][:].ravel()
        data["cost"] = f["/totals/total_cost"][:].ravel()
        data["startups"] = f["/state/startups"][:].ravel()

    datasets.append(data)
    all_startups.append(data["startups"])
    all_h2.append(data["h2"])
    all_co2.append(data["co2"])
    all_cost.append(data["cost"])

if not datasets:
    raise RuntimeError("All selected files were excluded by GROUP_FILTER.")

print("\n[INFO] Loaded datasets:")
for d in datasets:
    print(f"  {d['label']}")

# =====================================================
# Normalization
# =====================================================
norm = Normalize(
    vmin=np.percentile(np.concatenate(all_startups), 0),
    vmax=np.percentile(np.concatenate(all_startups), 99),
)
cmap = cm.jet

h2_lo, h2_hi = np.percentile(np.concatenate(all_h2), [P_LOW, P_HIGH])
co2_lo, co2_hi = np.percentile(np.concatenate(all_co2), [P_LOW, P_HIGH])
cost_lo, cost_hi = np.percentile(np.concatenate(all_cost), [P_LOW, P_HIGH])

# =====================================================
# Create figure
# =====================================================
fig = plt.figure(figsize=FIG_CONFIG["figsize"], dpi=FIG_CONFIG["dpi"])
ax = fig.add_axes(FIG_CONFIG["axes_pos"], projection="3d")

# =====================================================
# REMOVE ugly 3D background panes (HUGE improvement)
# =====================================================
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.xaxis.pane.set_edgecolor('white')
ax.yaxis.pane.set_edgecolor('white')
ax.zaxis.pane.set_edgecolor('white')

# =====================================================
# Improve box proportions (depth clarity)
# =====================================================
ax.set_box_aspect([1.0, 1.2, 0.6])

# =====================================================
# Plot
# =====================================================
for data in datasets:
    h2, co2, cost, startups = (
        data["h2"], data["co2"], data["cost"], data["startups"]
    )

    default_mask = np.zeros(len(startups), dtype=bool)
    default_mask[0] = True

    inlier = (
        (h2 >= h2_lo) & (h2 <= h2_hi) &
        (co2 >= co2_lo) & (co2 <= co2_hi) &
        (cost >= cost_lo) & (cost <= cost_hi)
    )

    plot_mask = inlier | default_mask

    # ✅ Crisp points (NO alpha blending blur)
    sc = ax.scatter(
        h2[plot_mask & ~default_mask],
        co2[plot_mask & ~default_mask],
        cost[plot_mask & ~default_mask],
        c=startups[plot_mask & ~default_mask],
        cmap=cmap,
        norm=norm,
        s=3,                     # slightly smaller = sharper
        alpha=1.0,              # IMPORTANT: removes blur
        edgecolors='none',      # clean rendering
        depthshade=False        # prevents weird shading
    )

    # Default point (keep emphasized)
    ax.scatter(
        h2[0], co2[0], cost[0],
        c=[startups[0]],
        cmap=cmap,
        norm=norm,
        marker="X",
        s=120,
        edgecolors="black",
        linewidths=1.5,
        zorder=100,
        depthshade=False
    )

# =====================================================
# Labels / formatting
# =====================================================
ax.set_xlabel("Total H$_2$ produced (kg)", fontsize=FIG_CONFIG["label_fontsize"])
ax.set_ylabel("Total CO$_2$ emitted (kg)", fontsize=FIG_CONFIG["label_fontsize"])
ax.set_zlabel("Electricity cost (USD)", fontsize=FIG_CONFIG["label_fontsize"])

ax.tick_params(labelsize=FIG_CONFIG["tick_fontsize"])

ax.xaxis.set_major_locator(MaxNLocator(FIG_CONFIG["n_ticks"]))
ax.yaxis.set_major_locator(MaxNLocator(FIG_CONFIG["n_ticks"]))
ax.zaxis.set_major_locator(MaxNLocator(FIG_CONFIG["n_ticks"]))

ax.set_xlim(h2_lo, h2_hi)
ax.set_ylim(co2_lo, co2_hi)
ax.set_zlim(cost_lo, cost_hi)

# =====================================================
# View (better perspective)
# =====================================================
ax.view_init(elev=20, azim=135)   # gives cleaner geometry
ax.grid(True)

# =====================================================
# Subtle grid styling (NOT dominant)
# =====================================================
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis._axinfo["grid"]['color'] = (0.3, 0.3, 0.3, 0.15)
    axis._axinfo["grid"]['linewidth'] = 0.4
    axis._axinfo["grid"]['linestyle'] = '--'

# =====================================================
# Thin axis lines (cleaner look)
# =====================================================
ax.xaxis.line.set_linewidth(0.8)
ax.yaxis.line.set_linewidth(0.8)
ax.zaxis.line.set_linewidth(0.8)

# =====================================================
# Colorbar (clean + modern)
# =====================================================
cax = fig.add_axes([0.80, 0.22, 0.015, 0.56])  # thinner + tighter
cbar = plt.colorbar(sc, cax=cax)

cbar.set_label("Electrolyzer startups",
               fontsize=FIG_CONFIG["cbar_label_fontsize"])
cbar.ax.tick_params(labelsize=FIG_CONFIG["tick_fontsize"])

# ✅ Remove heavy border
cbar.outline.set_visible(False)

# =====================================================
# Show (manual save workflow)
# =====================================================
plt.show()
