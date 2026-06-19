import h5py
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# ==================================================
# FONT SETTINGS
# ==================================================

FONT = {
    "title": 14,
    "labels": 14,
    "ticks": 12,
    "cbar_label": 14,
    "cbar_ticks": 12
}

plt.rcParams.update({
    "font.size": FONT["ticks"],
    "axes.titlesize": FONT["title"],
    "axes.labelsize": FONT["labels"],
    "xtick.labelsize": FONT["ticks"],
    "ytick.labelsize": FONT["ticks"]
})

# ==================================================
# SETTINGS
# ==================================================

DT_HR = 0.25   # 15-min timestep

# ==================================================
# PROJECT ROOT
# ==================================================

def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()
H5_PATH = PROJECT_ROOT / "outputs" / "results" / "default_case.h5"
#H5_PATH = PROJECT_ROOT / "outputs" / "results" / "clean_case.h5"

print(f"\nLoading: {H5_PATH}")

# ==================================================
# LOAD DATA
# ==================================================

with h5py.File(H5_PATH, "r") as f:
    time_raw = f["time"][:].ravel()
    h2_rate = f["sim/h2_kgph"][:].ravel()
    cost = f["sim/cost"][:].ravel()
    co2 = f["emissions/co2_kg_per_timestep"][:].ravel()

# ==================================================
# TIME CONVERSION
# ==================================================

if np.max(time_raw) > 1e9:
    time = pd.to_datetime(time_raw, unit="s")
else:
    raise ValueError("Unexpected time format")

years = time.year.values
unique_years = np.unique(years)

# ==================================================
# UNIT CONVERSION
# ==================================================

h2_kg = h2_rate * DT_HR

# ==================================================
# DERIVED METRICS
# ==================================================

valid = h2_kg > 1e-6

co2_per_h2 = np.full_like(co2, np.nan)
cost_per_h2 = np.full_like(cost, np.nan)

co2_per_h2[valid] = co2[valid] / h2_kg[valid]
cost_per_h2[valid] = cost[valid] / h2_kg[valid]

# ==================================================
# SYSTEM INTENSITY
# ==================================================

total_intensity = np.sum(co2[valid]) / np.sum(h2_kg[valid])
print(f"\n✅ Operational CO₂ intensity: {total_intensity:.2f} kg/kg")

# ==================================================
# PLOT
# ==================================================

fig, ax = plt.subplots(figsize=(7, 4))

# --------------------------------------------------
# Grey SMR Region (UNDERLAY)
# --------------------------------------------------

ax.axhspan(
    11, 14,
    color='red',
    alpha=0.1,
    label='Grey SMR',
    zorder=0
)

# --------------------------------------------------
# Scatter Plot
# --------------------------------------------------

sc = ax.scatter(
    cost_per_h2[valid],
    co2_per_h2[valid],
    c=years[valid],
    cmap="viridis_r",
    vmin=unique_years.min(),
    vmax=unique_years.max(),
    s=0.2,
    alpha=0.5,
    zorder=2
)

# ==================================================
# AXES LIMITS
# ==================================================

ax.set_xlim(-1, 5)
ax.set_ylim(0, 60)

# ==================================================
# LABELS
# ==================================================

ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)", fontsize=FONT["labels"])
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)", fontsize=FONT["labels"])

# ==================================================
# GRID + FRAME
# ==================================================

ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# Full frame
for spine in ax.spines.values():
    spine.set_visible(True)

# ==================================================
# LEGEND
# ==================================================

ax.legend(frameon=True)

# ==================================================
# COLORBAR
# ==================================================

cbar = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.03)
cbar.set_label("Year", fontsize=FONT["cbar_label"])
cbar.ax.tick_params(labelsize=FONT["cbar_ticks"])

# Format years as '20, '21, ..., '25
year_labels = [f"'{str(y)[-2:]}" for y in unique_years]

cbar.set_ticks(unique_years)
cbar.set_ticklabels(year_labels)


# ==================================================
# FINAL
# ==================================================

plt.tight_layout()
plt.show()