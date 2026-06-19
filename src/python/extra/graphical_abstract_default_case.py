import h5py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from pathlib import Path
from scipy.stats import gaussian_kde

DT_HR = 0.25

def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()
H5_PATH = PROJECT_ROOT / "outputs" / "results" / "default_case.h5"

with h5py.File(H5_PATH, "r") as f:
    time_raw = f["time"][:].ravel()
    h2_rate  = f["sim/h2_kgph"][:].ravel()
    cost     = f["sim/cost"][:].ravel()
    co2      = f["emissions/co2_kg_per_timestep"][:].ravel()

if np.max(time_raw) > 1e9:
    time = pd.to_datetime(time_raw, unit="s")
else:
    raise ValueError("Unexpected time format")

years        = time.year.values
unique_years = np.unique(years)
h2_kg        = h2_rate * DT_HR
valid        = h2_kg > 1e-6

co2_per_h2  = np.full_like(co2,  np.nan)
cost_per_h2 = np.full_like(cost, np.nan)
co2_per_h2[valid]  = co2[valid]  / h2_kg[valid]
cost_per_h2[valid] = cost[valid] / h2_kg[valid]

# ==================================================
# COLOR MAP — one color per year
# ==================================================

cmap        = plt.get_cmap("viridis_r")
year_colors = {y: cmap((y - unique_years.min()) / (unique_years.max() - unique_years.min()))
               for y in unique_years}

# ==================================================
# GRID FOR KDE
# ==================================================

x_min, x_max = -1, 5.4
y_min, y_max = 5, 60
xx, yy = np.mgrid[x_min:x_max:200j, y_min:y_max:200j]
grid_coords = np.vstack([xx.ravel(), yy.ravel()])

# ==================================================
# PLOT
# ==================================================

fig, ax = plt.subplots(figsize=(6, 3))

ax.axhspan(11, 14, color='red', alpha=0.1, zorder=0)

for year in unique_years:
    mask = valid & (years == year)
    x = cost_per_h2[mask]
    y = co2_per_h2[mask]

    in_range = (x >= x_min) & (x <= x_max) & (y >= y_min) & (y <= y_max)
    x, y = x[in_range], y[in_range]

    if len(x) < 10:
        continue

    kde = gaussian_kde(np.vstack([x, y]))
    z   = kde(grid_coords).reshape(xx.shape)

    color = year_colors[year]
    rgb   = color[:3]

    # Filled area — 2025 only
    if year == 2025:
        ax.contourf(
            xx, yy, z,
            levels=[z.max() * 0.05, z.max()],
            colors=[rgb],
            alpha=0.15,
            zorder=2
        )

    # Outline — all years
    ax.contour(
        xx, yy, z,
        levels=[z.max() * 0.05],
        colors=[rgb],
        alpha=0.8,
        linewidths=1.2,
        zorder=3
    )

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)

ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)", fontsize=12)
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)", fontsize=12)

ax.set_xticks([])
ax.set_yticks([])

ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# ==================================================
# REMOVE COLORBAR — no sm, no cbar
# ==================================================

# Add proxy artists for legend entries
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

legend_elements = []
for year in unique_years:
    color = year_colors[year]
    rgb   = color[:3]
    if year == 2025:
        legend_elements.append(
            Patch(facecolor=rgb, edgecolor=rgb, alpha=0.6, label=f"'{str(year)[-2:]}")
        )
    else:
        legend_elements.append(
            Line2D([0], [0], color=rgb, linewidth=1.5, label=f"'{str(year)[-2:]}")
        )

legend_elements.append(
    Patch(facecolor='red', edgecolor='red', alpha=0.2, label="Grey SMR")
)

plt.tight_layout()
plt.show()

# ==================================================
# LEGEND AS SEPARATE FIGURE
# ==================================================

fig_leg, ax_leg = plt.subplots(figsize=(4, 2))
ax_leg.axis("off")

ax_leg.legend(
    handles=legend_elements,
    loc="center",
    fontsize=10,
    frameon=False,
    ncol= 4,
    title="Year",
    title_fontsize=10
)

plt.tight_layout()
plt.show()