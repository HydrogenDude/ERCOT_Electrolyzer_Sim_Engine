import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

# ==================================================
# SETTINGS
# ==================================================

SETTINGS = {
    "cmap": "viridis",
    "vmin": 0,
    "vmax": 7,              # fixed range (no white space)
    "point_size": 3,
    "alpha": 0.6,
    "highlight_default": True
}

# ==================================================
# GLOBAL STYLE
# ==================================================

plt.rcParams.update({
    "font.size": 14,
    "axes.labelsize": 14,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14
})

# ==================================================
# LOAD DATA
# ==================================================

H5_PATH = r"C:/Users/evan123/Desktop/large_sim_results/N10000_S69_Doff_2025.h5"
print(f"\nLoading: {H5_PATH}")

with h5py.File(H5_PATH, "r") as f:
    total_cost = f["totals/total_cost"][:].ravel()
    total_co2  = f["totals/total_co2_kg"][:].ravel()
    total_h2   = f["totals/total_h2_kg"][:].ravel()

# ==================================================
# PROCESS DATA
# ==================================================

valid = total_h2 > 1e-6

cost_per_h2 = total_cost[valid] / total_h2[valid]
co2_per_h2  = total_co2[valid]  / total_h2[valid]
h2_total    = total_h2[valid] / 1000.0  # kg → metric tons

# ==================================================
# NORMALIZATION (FIXED RANGE 0–7)
# ==================================================

vmin = SETTINGS["vmin"]
vmax = SETTINGS["vmax"]

norm = Normalize(vmin=vmin, vmax=vmax)

# ✅ ensure full color usage
h2_plot = np.clip(h2_total, vmin, vmax)

# ==================================================
# FIGURE
# ==================================================

fig, ax = plt.subplots(figsize=(7, 4))

sc = ax.scatter(
    cost_per_h2,
    co2_per_h2,
    c=h2_plot,
    cmap=SETTINGS["cmap"],
    norm=norm,
    s=SETTINGS["point_size"],
    alpha=SETTINGS["alpha"],
    edgecolors="none"
)

# ==================================================
# DEFAULT CASE
# ==================================================

if SETTINGS["highlight_default"]:
    default_idx = 0
    default_color = plt.get_cmap(SETTINGS["cmap"])(norm(h2_plot[default_idx]))

    ax.scatter(
        cost_per_h2[default_idx],
        co2_per_h2[default_idx],
        marker="X",
        s=140,
        facecolors=default_color,
        edgecolors="black",
        linewidths=1.5,
        zorder=5,
        label="Default Case (avg. 2025)"
    )

# ==================================================
# AXES
# ==================================================

ax.set_xlabel("Cost per H$_2$ (USD/kg)")
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)")

ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# ==================================================
# LEGEND
# ==================================================

if SETTINGS["highlight_default"]:
    ax.legend(frameon=True)

# ==================================================
# COLORBAR
# ==================================================

cbar = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.03)
cbar.set_label("Total H$_2$ Produced (t)")

ticks = np.arange(vmin, vmax + 1, 1)
cbar.set_ticks(ticks)
cbar.set_ticklabels([str(t) for t in ticks])

cbar.ax.tick_params(labelsize=14)

# ==================================================
# FINAL
# ==================================================

plt.tight_layout()
plt.subplots_adjust(right=0.88)
plt.show()