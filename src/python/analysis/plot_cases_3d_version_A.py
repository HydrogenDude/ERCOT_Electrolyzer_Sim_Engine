import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog

# ==================================================
# PROJECT ROOT DETECTION
# ==================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# ==================================================
# OUTPUT PATH
# ==================================================
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
# File selection
# =====================================================
def select_h5_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    files = filedialog.askopenfilenames(
        title="Select HDF5 files",
        filetypes=[("HDF5 files", "*.h5")]
    )

    root.destroy()
    return [Path(f) for f in files]

h5_files = select_h5_files()
if not h5_files:
    raise RuntimeError("No files selected.")

# =====================================================
# Filename parser
# =====================================================
pattern = re.compile(
    r"N(?P<N>\d+)_S(?P<S>\d+)_D(?P<D>on|off)_(?P<year>\d{4})",
    re.IGNORECASE,
)

def dataset_selected(data, group_filter):
    if "DonOff" in group_filter and data.get("DonOff") not in group_filter["DonOff"]:
        return False
    if "year" in group_filter and data.get("year") not in group_filter["year"]:
        return False
    if "S" in group_filter and data.get("S") not in group_filter["S"]:
        return False
    return True

# =====================================================
# Load data
# =====================================================
all_h2, all_co2, all_cost, all_startups = [], [], [], []

for file in h5_files:
    meta = {}
    match = pattern.search(file.stem)

    if match:
        gd = match.groupdict()
        meta.update(
            DonOff=gd["D"].lower(),
            year=int(gd["year"]),
            S=int(gd["S"]),
        )
    else:
        meta.update(DonOff=None, year=None, S=None)

    if not dataset_selected(meta, GROUP_FILTER):
        continue

    with h5py.File(file, "r") as f:
        h2 = f["/totals/total_h2_kg"][:].ravel()
        co2 = f["/totals/total_co2_kg"][:].ravel()
        cost = f["/totals/total_cost"][:].ravel()
        startups = f["/state/startups"][:].ravel()

    all_h2.append(h2)
    all_co2.append(co2)
    all_cost.append(cost)
    all_startups.append(startups)

if not all_h2:
    raise RuntimeError("No datasets passed filtering.")

# =====================================================
# Combine datasets
# =====================================================
h2_all = np.concatenate(all_h2)
co2_all = np.concatenate(all_co2)
cost_all = np.concatenate(all_cost)
startups_all = np.concatenate(all_startups)

# Default point
h2_def = all_h2[0][0]
co2_def = all_co2[0][0]
cost_def = all_cost[0][0]
startups_def = all_startups[0][0]

# =====================================================
# Percentile filter
# =====================================================
h2_lo, h2_hi = np.percentile(h2_all, [P_LOW, P_HIGH])
co2_lo, co2_hi = np.percentile(co2_all, [P_LOW, P_HIGH])
cost_lo, cost_hi = np.percentile(cost_all, [P_LOW, P_HIGH])

mask = (
    (h2_all >= h2_lo) & (h2_all <= h2_hi) &
    (co2_all >= co2_lo) & (co2_all <= co2_hi) &
    (cost_all >= cost_lo) & (cost_all <= cost_hi)
)

# =====================================================
# Color normalization
# =====================================================
vmin = np.percentile(startups_all, 0)
vmax = np.percentile(startups_all, 99)
norm = Normalize(vmin=vmin, vmax=vmax)

# =====================================================
# USER-DEFINED AXIS BOUNDS ✅
# =====================================================
X_BOUNDS = (0, h2_hi)     # <- change freely
Y_BOUNDS = (0, 140000)    # <- change freely
Z_BOUNDS = (0, cost_hi)   # <- change freely

# =====================================================
# Plot
# =====================================================
fig = plt.figure(figsize=(7, 5))
ax = fig.add_subplot(111, projection='3d')

# Make panes (walls) white
ax.xaxis.pane.set_facecolor((1, 1, 1, 1))
ax.yaxis.pane.set_facecolor((1, 1, 1, 1))
ax.zaxis.pane.set_facecolor((1, 1, 1, 1))

# Remove pane edges (optional, cleaner look)
ax.xaxis.pane.set_edgecolor('white')
ax.yaxis.pane.set_edgecolor('white')
ax.zaxis.pane.set_edgecolor('white')

# Make overall figure background white
fig.patch.set_facecolor('white')

# Force axes background white
ax.set_facecolor('white')


# ✅ Main cloud
sc = ax.scatter(
    h2_all[mask],
    co2_all[mask],
    cost_all[mask],
    c=startups_all[mask],
    cmap='turbo',
    norm=norm,
    s=0.05,
    alpha=0.5
)

# =====================================================
# ✅ DEFAULT POINT — LARGE "X" WITH BLACK OUTLINE
# =====================================================

# Get colormap color for the default point
cmap = plt.get_cmap('turbo')
default_color = cmap(norm(startups_def))

ax.scatter(
    h2_def,
    co2_def,
    cost_def,

    # ✅ fill color (mapped)
    c=[default_color],

    # ✅ large marker
    s=250,

    # ✅ "X" shape
    marker='X',

    # ✅ BLACK outline
    edgecolors='black',
    linewidths=2.5,

    # ✅ ensure it's visible on top
    depthshade=False,
    zorder=100000
)

# =====================================================
# Labels + limits ✅
# =====================================================
ax.set_xlabel("Total H₂ produced (kg)", fontsize=14)
ax.set_ylabel("Total CO₂ emitted (kg)", fontsize=14)
ax.set_zlabel("Electricity cost (USD)", fontsize=14)

ax.set_xlim(*X_BOUNDS)
ax.set_ylim(*Y_BOUNDS)
ax.set_zlim(*Z_BOUNDS)

ax.view_init(elev=30, azim=-40)


# Light grid instead of dark gray
ax.grid(True, color='gray', alpha=0.25)

# Optional: remove back wall shading effect entirely
ax.xaxis._axinfo["grid"]['color'] = (0, 0, 0, 0.2)
ax.yaxis._axinfo["grid"]['color'] = (0, 0, 0, 0.2)
ax.zaxis._axinfo["grid"]['color'] = (0, 0, 0, 0.2)


# =====================================================
# Custom colorbar (better positioning)
# =====================================================
# Make room on the LEFT instead of right
plt.subplots_adjust(left=0.05)

# Place colorbar on left side
cbar_ax = fig.add_axes([0.08, 0.28, 0.025, 0.45])

cbar = fig.colorbar(sc, cax=cbar_ax)
cbar.set_label("Electrolyzer Startups")


# =====================================================
# Save
# =====================================================
output_path = OUTPUT_DIR / "3d_case_plot_matplotlib.pdf"
plt.savefig(output_path, dpi=600)

plt.show()