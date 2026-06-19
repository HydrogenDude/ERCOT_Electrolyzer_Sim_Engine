import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import matplotlib.lines as mlines
import matplotlib.patches as mpatches

# ==================================================
# SETTINGS
# ==================================================

SETTINGS = {
    "cmap": "viridis",
    "vmin": 0,
    "vmax": 7,
    "point_size": 3,
    "alpha": 0.6,
    "highlight_default": True,
    "show_smr_band": True,
    "smr_low": 11,
    "smr_high": 14,
    "smr_color": "red",
    "smr_alpha": 0.15,
    "smr_label": "Grey SMR"
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
# NORMALIZATION
# ==================================================

vmin = SETTINGS["vmin"]
vmax = SETTINGS["vmax"]

norm = Normalize(vmin=vmin, vmax=vmax)
h2_plot = np.clip(h2_total, vmin, vmax)

# ==================================================
# MAIN FIGURE
# ==================================================

fig, ax = plt.subplots(figsize=(5, 3))

# SMR BAND
if SETTINGS["show_smr_band"]:
    ax.axhspan(
        SETTINGS["smr_low"],
        SETTINGS["smr_high"],
        color=SETTINGS["smr_color"],
        alpha=SETTINGS["smr_alpha"],
        zorder=0
    )

# Scatter
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

# Default case
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
        zorder=5
    )

# Axes
ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)")
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)")
ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# Colorbar (kept in main figure)
cbar = fig.colorbar(sc, ax=ax, fraction=0.07, pad=0.03)
cbar.set_label("Total H$_2$ Produced (t)")
cbar.set_ticks(np.arange(vmin, vmax + 1, 1))
cbar.ax.tick_params(labelsize=14)

plt.tight_layout()
plt.subplots_adjust(right=0.88)
plt.show()


# ==================================================
# SEPARATE LEGEND FIGURE
# ==================================================

fig_leg, ax_leg = plt.subplots(figsize=(6, 2))

handles = []

# Scatter handle
scatter_handle = mlines.Line2D(
    [], [], marker='o', linestyle='None',
    markersize=8,
    color=plt.get_cmap(SETTINGS["cmap"])(0.7),
    label="Sim Case"
)
handles.append(scatter_handle)

# Default case
if SETTINGS["highlight_default"]:
    default_handle = mlines.Line2D(
        [], [], marker='X', linestyle='None',
        markersize=10,
        markerfacecolor='gray',
        markeredgecolor='black',
        label="Default Case"
    )
    handles.append(default_handle)

# SMR band
if SETTINGS["show_smr_band"]:
    smr_patch = mpatches.Patch(
        color=SETTINGS["smr_color"],
        alpha=SETTINGS["smr_alpha"],
        label=SETTINGS["smr_label"]
    )
    handles.append(smr_patch)

# Legend layout (horizontal)
ax_leg.legend(
    handles=handles,
    loc="center",
    frameon=False,
    fontsize=14,
    ncol=3,
    handlelength=1,
    columnspacing=1
)

ax_leg.axis('off')

plt.tight_layout()
plt.show()


# ==================================================
# OPTIONAL: SEPARATE COLORBAR FIGURE
# ==================================================

fig_cb, ax_cb = plt.subplots(figsize=(1.5, 4))

cbar2 = plt.colorbar(
    sc,
    cax=ax_cb,
    orientation='vertical'
)

cbar2.set_label("Total H$_2$ Produced (t)")
cbar2.set_ticks(np.arange(vmin, vmax + 1, 1))
ax_cb.tick_params(labelsize=12)

plt.tight_layout()
plt.show()