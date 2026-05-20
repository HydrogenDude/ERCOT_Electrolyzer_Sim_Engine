import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog

# ==================================================
# CONSTANTS
# ==================================================
HHV_H2_KWH_PER_KG = 39.4

# ==================================================
# PROJECT ROOT
# ==================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

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
# Filename parsing
# =====================================================
pattern = re.compile(
    r"N(?P<N>\d+)_S(?P<S>\d+)_D(?P<D>on|off)_(?P<year>\d{4})",
    re.IGNORECASE,
)

def dataset_selected(data, filters):
    return (
        data.get("DonOff") in filters["DonOff"] and
        data.get("year") in filters["year"] and
        data.get("S") in filters["S"]
    )

# =====================================================
# LOAD DATA
# =====================================================
all_eff, all_co2h2, all_costh2, all_startups = [], [], [], []

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
        energy = f["/totals/total_energy_MWh"][:].ravel()
        startups = f["/state/startups"][:].ravel()

    valid = h2 > 0

    h2 = h2[valid]
    co2 = co2[valid]
    cost = cost[valid]
    energy = energy[valid]
    startups = startups[valid]

    # ✅ Compute metrics
    eff = (h2 * HHV_H2_KWH_PER_KG) / (energy * 1000) * 100
    co2_per_h2 = co2 / h2
    cost_per_h2 = cost / h2

    all_eff.append(eff)
    all_co2h2.append(co2_per_h2)
    all_costh2.append(cost_per_h2)
    all_startups.append(startups)

if not all_eff:
    raise RuntimeError("No datasets passed filtering.")

# =====================================================
# Combine
# =====================================================
eff_all = np.concatenate(all_eff)
co2h2_all = np.concatenate(all_co2h2)
costh2_all = np.concatenate(all_costh2)
startups_all = np.concatenate(all_startups)

# Default point
eff_def = all_eff[0][0]
co2_def = all_co2h2[0][0]
cost_def = all_costh2[0][0]
startups_def = all_startups[0][0]

# =====================================================
# Percentile mask
# =====================================================
eff_lo, eff_hi = np.percentile(eff_all, [P_LOW, P_HIGH])
co2_lo, co2_hi = np.percentile(co2h2_all, [P_LOW, P_HIGH])
cost_lo, cost_hi = np.percentile(costh2_all, [P_LOW, P_HIGH])

mask = (
    (eff_all >= eff_lo) & (eff_all <= eff_hi) &
    (co2h2_all >= co2_lo) & (co2h2_all <= co2_hi) &
    (costh2_all >= cost_lo) & (costh2_all <= cost_hi)
)

# =====================================================
# Color normalization
# =====================================================
vmin = np.percentile(startups_all, 0)
vmax = np.percentile(startups_all, 99)
norm = Normalize(vmin=vmin, vmax=vmax)

# =====================================================
# Plot
# =====================================================
fig = plt.figure(figsize=(7, 5))
ax = fig.add_subplot(111, projection='3d')

# ✅ Clean white style
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis.pane.set_facecolor((1, 1, 1, 1))
    axis.pane.set_edgecolor('white')

fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# =====================================================
# CLOUD
# =====================================================
sc = ax.scatter(
    eff_all[mask],
    co2h2_all[mask],
    costh2_all[mask],
    c=startups_all[mask],
    cmap='turbo',
    norm=norm,
    s=.1,
    alpha=0.5
)

# =====================================================
# DEFAULT POINT (X)
# =====================================================
cmap = plt.get_cmap('turbo')
default_color = cmap(norm(startups_def))

ax.scatter(
    eff_def,
    co2_def,
    cost_def,
    c=[default_color],
    s=180,
    marker='X',
    edgecolors='black',
    linewidths=2.5,
    depthshade=False,
    zorder=10000
)

# =====================================================
# LABELS
# =====================================================
ax.set_xlabel("HHV Efficiency (%)", fontsize=14)
ax.set_ylabel("CO₂ per H₂ (kg/kg)", fontsize=14)
ax.set_zlabel("Cost per H₂ (USD/kg)", fontsize=14)

ax.view_init(elev=30, azim=-40)

# Light grid
ax.grid(True, color='gray', alpha=0.25)

# =====================================================
# COLORBAR (LEFT)
# =====================================================
plt.subplots_adjust(left=0.05)
cbar_ax = fig.add_axes([0.08, 0.28, 0.025, 0.45])
cbar = fig.colorbar(sc, cax=cbar_ax)
cbar.set_label("Electrolyzer Startups")

# =====================================================
# SAVE
# =====================================================
output_path = OUTPUT_DIR / "3d_efficiency_plot.pdf"
plt.savefig(output_path, dpi=600)

plt.show()