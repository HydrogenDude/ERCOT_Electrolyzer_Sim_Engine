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

P_LOW  = 0
P_HIGH = 88

GROUP_FILTER = {
    "DonOff": {"off"},
    "year": {2020, 2021, 2022, 2023, 2024, 2025},
    "S": {20, 69, 26},
}

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
# FILE SELECTION
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
# FILENAME PARSING
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
all_eff, all_co2, all_cost, all_startups = [], [], [], []

for file in h5_files:
    match = pattern.search(file.stem)
    if not match:
        continue

    gd = match.groupdict()
    meta = {
        "DonOff": gd["D"].lower(),
        "year": int(gd["year"]),
        "S": int(gd["S"]),
    }

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

    eff = 100 * (h2 * HHV_H2_KWH_PER_KG) / (energy * 1000)
    co2_per_h2 = co2 / h2
    cost_per_h2 = cost / h2

    all_eff.append(eff)
    all_co2.append(co2_per_h2)
    all_cost.append(cost_per_h2)
    all_startups.append(startups)

# Combine
eff_all = np.concatenate(all_eff)
co2_all = np.concatenate(all_co2)
cost_all = np.concatenate(all_cost)
startups_all = np.concatenate(all_startups)

# Default point
eff_def = all_eff[0][0]
co2_def = all_co2[0][0]
cost_def = all_cost[0][0]
startups_def = all_startups[0][0]

# =====================================================
# FILTER
# =====================================================
eff_lo, eff_hi = np.percentile(eff_all, [P_LOW, P_HIGH])
co2_lo, co2_hi = np.percentile(co2_all, [P_LOW, P_HIGH])
cost_lo, cost_hi = np.percentile(cost_all, [P_LOW, P_HIGH])

mask = (
    (eff_all >= eff_lo) & (eff_all <= eff_hi) &
    (co2_all >= co2_lo) & (co2_all <= co2_hi) &
    (cost_all >= cost_lo) & (cost_all <= cost_hi)
)

# =====================================================
# COLOR
# =====================================================
vmin = np.percentile(startups_all, 1)
vmax = np.percentile(startups_all, 99)
norm = Normalize(vmin=vmin, vmax=vmax)
cmap = plt.get_cmap("turbo")

# =====================================================
# STYLE
# =====================================================
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 14,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10
})

# =====================================================
# PLOTTING FUNCTION ✅ FIXED
# =====================================================
def create_plot(x, y, xlabel, ylabel, filename, x_def, y_def):

    fig, ax = plt.subplots(figsize=(7, 4))

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    sc = ax.scatter(
        x[mask],
        y[mask],
        c=startups_all[mask],
        cmap=cmap,
        norm=norm,
        s=3,
        alpha=0.5
    )

    # ✅ Correct default point
    default_color = cmap(norm(startups_def))
    ax.scatter(
        x_def,
        y_def,
        c=[default_color],
        s=180,
        marker='X',
        edgecolors='black',
        linewidths=2.5,
        zorder=100
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    ax.grid(True, color='gray', alpha=0.25)

    # ✅ Better colorbar spacing
    plt.subplots_adjust(left=0.18)
    cbar_ax = fig.add_axes([0.11, 0.22, 0.025, 0.58])
    cbar = fig.colorbar(sc, cax=cbar_ax)
    cbar.set_label("Electrolyzer Startups")

    plt.tight_layout(rect=[0.20, 0, 1, 1])
    fig.savefig(OUTPUT_DIR / filename, bbox_inches='tight', dpi=600)

# =====================================================
# CREATE PLOTS ✅
# =====================================================

# 1. Efficiency vs Cost
create_plot(
    eff_all, cost_all,
    "HHV Efficiency (%)",
    "Cost per H$_2$ (USD/kg)",
    "eff_vs_cost_clean.pdf",
    eff_def, cost_def
)

# 2. Efficiency vs CO2
create_plot(
    eff_all, co2_all,
    "HHV Efficiency (%)",
    "CO$_2$ per H$_2$ (kg/kg)",
    "eff_vs_co2_clean.pdf",
    eff_def, co2_def
)

# ✅ 3. NEW: CO2 vs Cost
create_plot(
    co2_all, cost_all,
    "CO$_2$ per H$_2$ (kg/kg)",
    "Cost per H$_2$ (USD/kg)",
    "co2_vs_cost_clean.pdf",
    co2_def, cost_def
)

print(f"\n✅ Saved styled plots to: {OUTPUT_DIR}")
plt.show()
