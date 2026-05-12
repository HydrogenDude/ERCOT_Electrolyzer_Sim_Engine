import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
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
# FILE SELECTION VIA POPUP (MULTI-SELECT)
# =====================================================
def select_h5_files():
    root = tk.Tk()
    root.withdraw()         # hide main tkinter window
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

print("\n[INFO] User-selected files:")
for f in h5_files:
    print(f"  {f}")

# =====================================================
# Filename parser (best-effort)
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
all_startups = []
all_h2 = []
all_co2 = []
all_cost = []

for h5file in h5_files:
    meta = {}
    match = pattern.search(h5file.stem)

    if match:
        gd = match.groupdict()
        meta.update(
            DonOff=gd["D"].lower(),
            year=int(gd["year"]),
            S=int(gd["S"])
        )
    else:
        # allow unconventional names
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
    print(f"     → {d['filepath']}")

# =====================================================
# Global color normalization
# =====================================================
norm = Normalize(
    vmin=np.percentile(np.concatenate(all_startups), 0),
    vmax=np.percentile(np.concatenate(all_startups), 99),
)
cmap = cm.jet

# =====================================================
# Percentile plot window
# =====================================================
h2_lo, h2_hi = np.percentile(np.concatenate(all_h2), [P_LOW, P_HIGH])
co2_lo, co2_hi = np.percentile(np.concatenate(all_co2), [P_LOW, P_HIGH])
cost_lo, cost_hi = np.percentile(np.concatenate(all_cost), [P_LOW, P_HIGH])

# =====================================================
# Figure
# =====================================================
fig = plt.figure(figsize=(7, 5), dpi=110)
ax = fig.add_subplot(111, projection="3d")

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
        (h2   >= h2_lo) & (h2   <= h2_hi) &
        (co2  >= co2_lo) & (co2  <= co2_hi) &
        (cost >= cost_lo) & (cost <= cost_hi)
    )

    plot_mask = inlier | default_mask

    sc = ax.scatter(
        h2[plot_mask & ~default_mask],
        co2[plot_mask & ~default_mask],
        cost[plot_mask & ~default_mask],
        c=startups[plot_mask & ~default_mask],
        cmap=cmap,
        norm=norm,
        s=3,
        alpha=0.7,
        linewidth=0,
    )

    # Default case
    ax.scatter(
        h2[0], co2[0], cost[0],
        c=[startups[0]],
        cmap=cmap,
        norm=norm,
        marker="X",
        s=120,
        edgecolors="black",
        linewidths=2,
        zorder=100,
    )

# =====================================================
# Labels and formatting
# =====================================================
ax.set_xlabel("Total H$_2$ produced (kg)")
ax.set_ylabel("Total CO$_2$ emitted (kg)")
ax.set_zlabel("Electricity cost (USD)")
ax.view_init(elev=30, azim=-40)
ax.set_xlim(h2_lo, h2_hi)
ax.set_ylim(co2_lo, co2_hi)
ax.set_zlim(cost_lo, cost_hi)
ax.grid(False)

cax = fig.add_axes([0.85, 0.25, 0.025, 0.5])
cbar = plt.colorbar(sc, cax=cax)
cbar.set_label("Electrolyzer startups\n(0–99 percentile normalized)")

plt.show()