import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from pathlib import Path

# ----------------------------------------------------
# Resolve project root and load HDF5
# ----------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
h5file = PROJECT_ROOT / "outputs" / "results" / "results_timeseries.h5"

with h5py.File(h5file, "r") as f:
    total_h2_kg  = f["/totals/total_h2_kg"][:].reshape(-1)
    total_co2_kg = f["/totals/total_co2_kg"][:].reshape(-1)
    total_cost   = f["/totals/total_cost"][:].reshape(-1)
    startups     = f["/state/startups"][:].reshape(-1)

# ----------------------------------------------------
# Percentile-clipped normalization
# ----------------------------------------------------
vmin = np.percentile(startups, 10)
vmax = np.percentile(startups, 90)

norm = Normalize(vmin=vmin, vmax=vmax)
cmap = cm.jet

# ----------------------------------------------------
# Separate default case (ID = 1)
# ----------------------------------------------------
default_mask = np.zeros_like(startups, dtype=bool)
default_mask[0] = True
other_mask = ~default_mask

# ----------------------------------------------------
# Figure & 3D axes
# ----------------------------------------------------
fig = plt.figure(figsize=(7, 5), dpi=110)
ax = fig.add_subplot(111, projection="3d")

# ---- Other cases ----
sc = ax.scatter(
    total_h2_kg[other_mask],
    total_co2_kg[other_mask],
    total_cost[other_mask],
    c=startups[other_mask],
    cmap=cmap,
    norm=norm,
    s=18,
    alpha=1.0,
    linewidth=0
)

# ---- Default case ----
ax.scatter(
    total_h2_kg[default_mask],
    total_co2_kg[default_mask],
    total_cost[default_mask],
    c=startups[default_mask],
    cmap=cmap,
    norm=norm,
    s=60,
    alpha=1.0,
    edgecolors="black",
    linewidths=1.3,
    zorder=1000
)

# ----------------------------------------------------
# Labels
# ----------------------------------------------------
ax.set_xlabel("Total H$_2$ produced (kg)", labelpad=10)
ax.set_ylabel("Total CO$_2$ emitted (kg)", labelpad=10)
ax.set_zlabel("Electricity cost", labelpad=14)

# ----------------------------------------------------
# Camera and limits
# ----------------------------------------------------
ax.view_init(elev=35, azim=-100)

ax.set_xlim(0, total_h2_kg.max() * 1.05)
ax.set_ylim(0, total_co2_kg.max() * 1.05)
ax.set_zlim(0, total_cost.max() * 1.05)

ax.grid(False)

# ----------------------------------------------------
# Manual layout control (CRITICAL)
# ----------------------------------------------------
plt.subplots_adjust(
    left=0.0,
    right=1.0,
    bottom=0.12,
    top=0.90
)

# ----------------------------------------------------
# Colorbar (manually positioned)
# ----------------------------------------------------
cax = fig.add_axes([0.85, 0.25, 0.025, 0.5])
cbar = plt.colorbar(sc, cax=cax)
cbar.set_label(
    "Electrolyzer startups\n(10th–90th percentile normalized)"
)

# ----------------------------------------------------
# Title
# ----------------------------------------------------
#ax.set_title(
#    "Trade space: hydrogen output, emissions, and cost",
#    fontsize=11,
#    pad=12
#)

plt.show()