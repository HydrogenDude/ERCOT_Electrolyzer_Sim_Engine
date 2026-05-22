import h5py
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import matplotlib.dates as mdates

# ==================================================
# SETTINGS
# ==================================================

TIME_STEP_MIN = 15
WINDOW_DAYS = 14
STEPS_PER_DAY = int(24 * 60 / TIME_STEP_MIN)
ROLL_WINDOW = WINDOW_DAYS * STEPS_PER_DAY

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

print(f"\nLoading: {H5_PATH}")

# ==================================================
# LOAD DATA
# ==================================================

with h5py.File(H5_PATH, "r") as f:
    time_raw = f["time"][:].ravel()
    P = f["sim/P_grid_kW"][:].ravel()
    h2_rate = f["sim/h2_kgph"][:].ravel()
    cost = f["sim/cost"][:].ravel()
    co2 = f["emissions/co2_kg_per_timestep"][:].ravel()

# ==================================================
# ✅ FIXED TIME CONVERSION (ROBUST)
# ==================================================

if np.max(time_raw) > 1e9:
    # Unix seconds → correct case
    time = pd.to_datetime(time_raw, unit="s")
else:
    raise ValueError("Unexpected time format in dataset")

# Optional check
print("\nTime preview:")
print(time[:5])

# ==================================================
# DERIVED METRICS
# ==================================================

valid = h2_rate > 1e-6

co2_per_h2 = np.full_like(co2, np.nan)
cost_per_h2 = np.full_like(cost, np.nan)

co2_per_h2[valid] = co2[valid] / h2_rate[valid]
cost_per_h2[valid] = cost[valid] / h2_rate[valid]

# Rolling averages (14-day smoothing)
P_avg = pd.Series(P).rolling(ROLL_WINDOW, center=True).mean()
h2_avg = pd.Series(h2_rate).rolling(ROLL_WINDOW, center=True).mean()
cost_avg = pd.Series(cost_per_h2).rolling(ROLL_WINDOW, center=True).mean()
co2_avg = pd.Series(co2_per_h2).rolling(ROLL_WINDOW, center=True).mean()

# Utilization
is_on = (P > 0).astype(float)
utilization = pd.Series(is_on).rolling(ROLL_WINDOW).mean()

# Cumulative totals
dt_hr = TIME_STEP_MIN / 60
H2_total = np.nancumsum(h2_rate * dt_hr)
cost_total = np.nancumsum(cost)
co2_total = np.nancumsum(co2)

# ==================================================
# STYLE
# ==================================================

plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 13,
})

# ==================================================
# 1. SYSTEM POWER
# ==================================================

plt.figure(figsize=(12,4))
plt.plot(time, P, alpha=0.15, label="15-min")
plt.plot(time, P_avg, linewidth=2, label="14-day avg")
plt.ylabel("Power (kW)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 2. H2 PRODUCTION
# ==================================================

plt.figure(figsize=(12,4))
plt.plot(time, h2_rate, alpha=0.15)
plt.plot(time, h2_avg, linewidth=2)
plt.ylabel("H$_2$ Production (kg/h)")
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 3. CO2 INTENSITY
# ==================================================

plt.figure(figsize=(12,4))
plt.plot(time, co2_per_h2, alpha=0.08)
plt.plot(time, co2_avg, linewidth=2)
plt.ylabel("CO$_2$ per H$_2$ (kg/kg)")
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 4. COST INTENSITY
# ==================================================

plt.figure(figsize=(12,4))
plt.plot(time, cost_per_h2, alpha=0.08)
plt.plot(time, cost_avg, linewidth=2)
plt.ylabel("Cost per H$_2$ (USD/kg)")
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 5. CO2 vs COST (KEY TRADEOFF, COLORED BY YEAR)
# ==================================================

# Extract year from time
years = pd.to_datetime(time).year.values

plt.figure(figsize=(6,4))

sc = plt.scatter(
    cost_per_h2[valid],
    co2_per_h2[valid],
    c=years[valid],          # ✅ color by year
    cmap="viridis_r",          # good default; can change
    s=2,
    alpha=0.4
)

plt.xlabel("Cost per H$_2$ (USD/kg)")
plt.ylabel("CO$_2$ per H$_2$ (kg/kg)")
plt.grid(alpha=1.0)

# Colorbar
cbar = plt.colorbar(sc)
cbar.set_label("Year")

plt.tight_layout()

# ==================================================
# 6. POWER vs H2 (PHYSICS CHECK)
# ==================================================

plt.figure(figsize=(6,4))
plt.scatter(P[valid], h2_rate[valid], s=2, alpha=0.3)
plt.xlabel("Power (kW)")
plt.ylabel("H$_2$ Production (kg/h)")
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 7. CUMULATIVE TOTALS
# ==================================================

plt.figure(figsize=(12,4))
plt.plot(time, H2_total, label="H$_2$ (kg)")
plt.plot(time, cost_total, label="Cost (USD)")
plt.plot(time, co2_total, label="CO$_2$ (kg)")
plt.legend()
plt.ylabel("Cumulative")
plt.grid(alpha=0.3)
plt.tight_layout()

# ==================================================
# 8. UTILIZATION
# ==================================================

plt.figure(figsize=(12,3))
plt.plot(time, utilization)
plt.ylabel("Utilization")
plt.ylim(0,1)
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()