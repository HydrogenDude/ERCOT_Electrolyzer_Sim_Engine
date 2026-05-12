import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from pathlib import Path
import re
import os

# =====================================================
# Configuration
# =====================================================
P_LOW  = 0
P_HIGH = 89

# --------- EXPLICIT GROUP SELECTION (EDIT HERE) -------
GROUP_FILTER = {
    "DonOff": {"off"},                       # {"on"}, {"off"}, or {"on", "off"}
    "year": {2020, 2025},
    "S": {20, 69},                               # filter by S number
    #"label": {"default_case_results_2020_thru_2025"},       # optional exact file names (stem)
}
# -----------------------------------------------------


# =====================================================
# Resolve project root and search locations
# =====================================================
PROJECT_ROOT = Path(__file__).resolve().parents[3]

SEARCH_DIRS = [
    PROJECT_ROOT / "outputs" / "results",                              # default location
    Path(__file__).resolve().parent,                                     # script directory
    Path(r"C:\Users\evan123\Desktop\large_sim_results"),                 # ✅ EXTERNAL FOLDER
]

H5_GLOB = "N*_S*_D*_*.h5"


# =====================================================
# Locate HDF5 files (deduplicated)
# =====================================================
h5_files = {}
missing_dirs = []

for d in SEARCH_DIRS:
    if not d.exists():
        missing_dirs.append(d)
        continue

    for f in d.glob(H5_GLOB):
        h5_files[f.resolve()] = f

h5_files = sorted(h5_files.values())

if missing_dirs:
    print("\n[WARN] The following search directories do not exist:")
    for d in missing_dirs:
        print(f"  - {d}")

if not h5_files:
    raise RuntimeError(
        f"No HDF5 files matching '{H5_GLOB}' found in any SEARCH_DIRS."
    )

print("\n[INFO] Located HDF5 files:")
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
    if "DonOff" in group_filter and data["DonOff"] not in group_filter["DonOff"]:
        return False
    if "year" in group_filter and data["year"] not in group_filter["year"]:
        return False
    if "S" in group_filter and data["S"] not in group_filter["S"]:
        return False
    if "label" in group_filter and data["label"] not in group_filter["label"]:
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
    match = pattern.search(h5file.stem)
    if not match:
        continue

    meta = match.groupdict()

    data = dict(
        DonOff=meta["D"].lower(),
        year=int(meta["year"]),
        S=int(meta["S"]),
        label=h5file.stem,
        filepath=str(h5file),
    )

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
    raise RuntimeError("GROUP_FILTER excluded all datasets.")


print("\n[INFO] Selected datasets:")
for d in datasets:
    print(f"  {d['label']}  (S{d['S']}, D{d['DonOff']}, {d['year']})")
    print(f"     → {d['filepath']}")


# =====================================================
# Global color normalization
# =====================================================
all_startups = np.concatenate(all_startups)
norm = Normalize(
    vmin=np.percentile(all_startups, 0),
    vmax=np.percentile(all_startups, 99),
)
cmap = cm.jet


# =====================================================
# Percentile plot window
# =====================================================
all_h2   = np.concatenate(all_h2)
all_co2  = np.concatenate(all_co2)
all_cost = np.concatenate(all_cost)

h2_lo, h2_hi       = np.percentile(all_h2,   [P_LOW, P_HIGH])
co2_lo, co2_hi     = np.percentile(all_co2,  [P_LOW, P_HIGH])
cost_lo, cost_hi   = np.percentile(all_cost, [P_LOW, P_HIGH])


# =====================================================
# Alpha mapping by year
# =====================================================
years = sorted({d["year"] for d in datasets})
alpha_min, alpha_max = 0.3, 0.5

alpha_map = {
    year: alpha_min + (alpha_max - alpha_min)
          * (i / max(len(years) - 1, 1))
    for i, year in enumerate(years)
}


# =====================================================
# Figure
# =====================================================
fig = plt.figure(figsize=(7, 5), dpi=110)
ax = fig.add_subplot(111, projection="3d")


# =====================================================
# Plot + reporting
# =====================================================
total_points = visible_points = hidden_points = 0

print("\n[INFO] Outlier filtering report")
print(f"       Percentile window: {P_LOW}–{P_HIGH}\n")

for data in datasets:
    h2, co2, cost, startups = data["h2"], data["co2"], data["cost"], data["startups"]
    n = len(startups)

    total_points += n

    default_mask = np.zeros(n, dtype=bool)
    default_mask[0] = True

    inlier = (
        (h2   >= h2_lo)   & (h2   <= h2_hi) &
        (co2  >= co2_lo)  & (co2  <= co2_hi) &
        (cost >= cost_lo) & (cost <= cost_hi)
    )

    plot_mask = inlier | default_mask
    shown = plot_mask.sum()
    hidden = n - shown

    visible_points += shown
    hidden_points += hidden

    print(f"  {data['label']}: total={n}, plotted={shown}, hidden={hidden}")

    sc = ax.scatter(
        h2[plot_mask & ~default_mask],
        co2[plot_mask & ~default_mask],
        cost[plot_mask & ~default_mask],
        c=startups[plot_mask & ~default_mask],
        cmap=cmap,
        norm=norm,
        s=5,
        alpha=alpha_map[data["year"]],
        linewidth=0,
    )

    # Default case
    ax.scatter(h2[0], co2[0], cost[0], color="white", s=130, zorder=998)
    ax.scatter(
        h2[0], co2[0], cost[0],
        c=[startups[0]], cmap=cmap, norm=norm,
        marker="X", s=100, edgecolors="black", linewidths=1.8, zorder=1000
    )


# =====================================================
# Summary
# =====================================================
print("\n[SUMMARY]")
print(f"  Total points loaded : {total_points}")
print(f"  Points plotted      : {visible_points}")
print(f"  Points hidden       : {hidden_points}")
print(f"  Hidden fraction     : {hidden_points / total_points:.2%}")


# =====================================================
# Labels and view
# =====================================================
ax.set_xlabel("Total H$_2$ produced (kg)")
ax.set_ylabel("Total CO$_2$ emitted (kg)")
ax.set_zlabel("Electricity cost (USD)")

ax.view_init(elev=30, azim=-140)
ax.set_xlim(h2_lo, h2_hi)
ax.set_ylim(co2_lo, co2_hi)
ax.set_zlim(cost_lo, cost_hi)
ax.grid(False)

plt.subplots_adjust(left=0.0, right=1.0, bottom=0.12, top=0.90)


# =====================================================
# Colorbar
# =====================================================
cax = fig.add_axes([0.85, 0.25, 0.025, 0.5])
cbar = plt.colorbar(sc, cax=cax)
cbar.set_label("Electrolyzer startups\n(0–99 percentile normalized)")

plt.show()
