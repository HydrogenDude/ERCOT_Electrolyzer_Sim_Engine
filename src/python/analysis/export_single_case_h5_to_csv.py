"""
Export single-case HDF5 results to CSV with:
  - Case-level totals
  - Per-timestep time series
  - Per-year performance metrics
"""

import h5py
import numpy as np
import pandas as pd
from pathlib import Path


# ----------------------------------------------------
# Paths
# ----------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
h5_file = PROJECT_ROOT / "outputs" / "results" / "default_case_results_2020_thru_2025.h5"
csv_file = PROJECT_ROOT / "outputs" / "tables" / "default_case_results_2020_thru_2025.csv"


# ----------------------------------------------------
# Load HDF5
# ----------------------------------------------------
with h5py.File(h5_file, "r") as f:

    case_id = f["/case_id"][:].reshape(-1)
    if len(case_id) != 1:
        raise ValueError("Expected exactly one case")

    time_posix = f["/time"][:].reshape(-1)
    time = pd.to_datetime(time_posix, unit="s")

    P_grid_kW = f["/sim/P_grid_kW"][:].reshape(-1)
    h2_kgph   = f["/sim/h2_kgph"][:].reshape(-1)
    cost_ts   = f["/sim/cost"][:].reshape(-1)
    co2_ts    = f["/emissions/co2_kg_per_timestep"][:].reshape(-1)

    startups = int(f["/state/startups"][0])


# ----------------------------------------------------
# Timestep duration (hours)
# ----------------------------------------------------
dt_hr = (time[1] - time[0]).total_seconds() / 3600.0


# ----------------------------------------------------
# Build time-series DataFrame
# ----------------------------------------------------
df_ts = pd.DataFrame(
    {
        "time": time,
        "P_grid_kW": P_grid_kW,
        "h2_kgph": h2_kgph,
        "cost": cost_ts,
        "co2_kg": co2_ts,
    }
)

df_ts["year"] = df_ts["time"].dt.year
df_ts["energy_MWh"] = df_ts["P_grid_kW"] * dt_hr / 1000
df_ts["h2_kg"] = df_ts["h2_kgph"] * dt_hr
df_ts["operating"] = df_ts["P_grid_kW"] > 0


# ----------------------------------------------------
# Per-year aggregation
# ----------------------------------------------------
P_rated_kW = df_ts["P_grid_kW"].max()

yearly = (
    df_ts
    .groupby("year")
    .agg(
        h2_kg=("h2_kg", "sum"),
        co2_kg=("co2_kg", "sum"),
        energy_MWh=("energy_MWh", "sum"),
        cost=("cost", "sum"),
        operating_hours=("operating", "sum"),
        total_steps=("operating", "count"),
    )
    .reset_index()
)

yearly["hours"] = yearly["total_steps"] * dt_hr
yearly["capacity_factor"] = yearly["energy_MWh"] / (P_rated_kW * yearly["hours"] / 1000)
yearly["utilization_rate"] = yearly["operating_hours"] / yearly["total_steps"]
yearly["cost_per_kg_h2"] = yearly["cost"] / yearly["h2_kg"]
yearly["co2_intensity_kg_per_kg_h2"] = yearly["co2_kg"] / yearly["h2_kg"]

weighted_utilization = np.average(
    yearly["utilization_rate"],
    weights=yearly["hours"]
)

# ----------------------------------------------------
# Total / average metrics
# ----------------------------------------------------
totals = pd.DataFrame(
    [{
        "h2_kg": yearly["h2_kg"].sum(),
        "co2_kg": yearly["co2_kg"].sum(),
        "energy_MWh": yearly["energy_MWh"].sum(),
        "cost": yearly["cost"].sum(),
        "capacity_factor": (
            yearly["energy_MWh"].sum()
            / (P_rated_kW * yearly["hours"].sum() / 1000)
        ),
        "utilization_rate": weighted_utilization,
        "cost_per_kg_h2": yearly["cost"].sum() / yearly["h2_kg"].sum(),
        "co2_intensity_kg_per_kg_h2": yearly["co2_kg"].sum() / yearly["h2_kg"].sum(),
        "startups": startups,
    }]
)



# ----------------------------------------------------
# Write CSV (three blocks)
# ----------------------------------------------------
with open(csv_file, "w", newline="") as f:
    f.write("# --- totals ---\n")
    totals.to_csv(f, index=False)

    f.write("\n# --- yearly_metrics ---\n")
    yearly.to_csv(f, index=False)

    f.write("\n# --- time_series ---\n")
    df_ts.drop(columns=["year"]).to_csv(f, index=False)


print("[OK] Export complete")
print(f"     File: {csv_file}")
