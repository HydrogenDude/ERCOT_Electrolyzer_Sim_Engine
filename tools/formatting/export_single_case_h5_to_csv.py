"""
Export single-case HDF5 results to CSV with:
  - Case-level totals
  - Per-timestep time series
  - Per-year performance metrics
  - Added:
      * Mean price (ON / OFF)
      * Mean ON/OFF duration
      * Startups per year + average
      * H2 per startup

NOTE:
- Electricity price loaded from data/inputs/price.txt (timestamped)
- Matched to simulation time using timestamps (robust)
"""

import h5py
import numpy as np
import pandas as pd
from pathlib import Path



# ----------------------------------------------------
# Project root detection
# ----------------------------------------------------
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

# ----------------------------------------------------
# Paths
# ----------------------------------------------------
PROJECT_ROOT = get_project_root()
h5_file = PROJECT_ROOT / "outputs" / "results" / "default_case.h5"
csv_file = PROJECT_ROOT / "outputs" / "tables" / "default_case.csv"
price_file = PROJECT_ROOT / "data" / "inputs" / "price.txt"


# ----------------------------------------------------
# Load HDF5 (UNCHANGED)
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

    startups_total = int(f["/state/startups"][0].item())


# ----------------------------------------------------
# Timestep duration
# ----------------------------------------------------
dt_hr = (time[1] - time[0]).total_seconds() / 3600.0


# ----------------------------------------------------
# Build base DataFrame (UNCHANGED LOGIC)
# ----------------------------------------------------
df_ts = pd.DataFrame({
    "time": time,
    "P_grid_kW": P_grid_kW,
    "h2_kgph": h2_kgph,
    "cost_signal": cost_ts,
    "co2_kg": co2_ts,
})


# ----------------------------------------------------
# ✅ NEW: Load and align price data by timestamp
# ----------------------------------------------------
price_df = pd.read_csv(price_file)

# Parse timestamps
price_df["time"] = pd.to_datetime(price_df["Timestamp"])

# Ensure column name consistency
price_df = price_df.rename(columns={"Price": "price_per_MWh"})

# Merge on time (THIS IS THE KEY FIX)
df_ts = df_ts.merge(price_df[["time", "price_per_MWh"]], on="time", how="left")

# ✅ Check for missing matches
if df_ts["price_per_MWh"].isna().any():
    missing_frac = df_ts["price_per_MWh"].isna().mean()
    raise ValueError(
        f"Price alignment failed: {missing_frac:.2%} of timesteps missing price data"
    )


# ----------------------------------------------------
# Continue normal processing
# ----------------------------------------------------
df_ts["year"] = df_ts["time"].dt.year
df_ts["energy_MWh"] = df_ts["P_grid_kW"] * dt_hr / 1000
df_ts["h2_kg"] = df_ts["h2_kgph"] * dt_hr
df_ts["operating"] = df_ts["P_grid_kW"] > 0

# ✅ TRUE cost using price
df_ts["cost_$"] = df_ts["energy_MWh"] * df_ts["price_per_MWh"]


# ----------------------------------------------------
# ON / OFF runs
# ----------------------------------------------------
state_change = df_ts["operating"].ne(df_ts["operating"].shift())
df_ts["run_id"] = state_change.cumsum()

run_tbl = (
    df_ts
    .groupby("run_id")
    .agg(
        year=("year", "first"),
        operating=("operating", "first"),
        duration_steps=("operating", "size"),
        h2_kg=("h2_kg", "sum"),
    )
    .reset_index()
)

run_tbl["duration_hr"] = run_tbl["duration_steps"] * dt_hr


# ----------------------------------------------------
# Price metrics (NOW FULLY CORRECT)
# ----------------------------------------------------
price_metrics = (
    df_ts
    .groupby("year")
    .apply(lambda g: pd.Series({

        "mean_price_on":
            np.average(
                g.loc[g["operating"], "price_per_MWh"],
                weights=g.loc[g["operating"], "energy_MWh"]
            ) if g["operating"].any() else np.nan,

        "mean_price_off":
            g.loc[~g["operating"], "price_per_MWh"].mean()
    }))
    .reset_index()
)


# ----------------------------------------------------
# Duration + startup metrics
# ----------------------------------------------------
duration_metrics = (
    run_tbl
    .groupby("year")
    .apply(lambda g: pd.Series({
        "mean_on_duration_hr":
            g.loc[g["operating"], "duration_hr"].mean(),

        "mean_off_duration_hr":
            g.loc[~g["operating"], "duration_hr"].mean(),

        "startups":
            int(g["operating"].sum()),

        "h2_per_startup_kg":
            g.loc[g["operating"], "h2_kg"].sum() /
            max(1, int(g["operating"].sum()))
    }))
    .reset_index()
)


# ----------------------------------------------------
# Yearly aggregation
# ----------------------------------------------------
P_rated_kW = df_ts["P_grid_kW"].max()

yearly = (
    df_ts
    .groupby("year")
    .agg(
        h2_kg=("h2_kg", "sum"),
        co2_kg=("co2_kg", "sum"),
        energy_MWh=("energy_MWh", "sum"),
        cost=("cost_$", "sum"),
        operating_hours=("operating", "sum"),
        total_steps=("operating", "count"),
    )
    .reset_index()
)

yearly["hours"] = yearly["total_steps"] * dt_hr
yearly["capacity_factor"] = yearly["energy_MWh"] / (
    P_rated_kW * yearly["hours"] / 1000
)
yearly["utilization_rate"] = yearly["operating_hours"] / yearly["total_steps"]
yearly["cost_per_kg_h2"] = yearly["cost"] / yearly["h2_kg"]
yearly["co2_intensity_kg_per_kg_h2"] = yearly["co2_kg"] / yearly["h2_kg"]


# ----------------------------------------------------
# Merge metrics
# ----------------------------------------------------
yearly = (
    yearly
    .merge(price_metrics, on="year", how="left")
    .merge(duration_metrics, on="year", how="left")
)


# ----------------------------------------------------
# Totals
# ----------------------------------------------------
weighted_utilization = np.average(
    yearly["utilization_rate"],
    weights=yearly["hours"]
)

totals = pd.DataFrame([{

    "h2_kg": yearly["h2_kg"].sum(),
    "co2_kg": yearly["co2_kg"].sum(),
    "energy_MWh": yearly["energy_MWh"].sum(),
    "cost": yearly["cost"].sum(),

    "capacity_factor":
        yearly["energy_MWh"].sum() /
        (P_rated_kW * yearly["hours"].sum() / 1000),

    "utilization_rate": weighted_utilization,

    "cost_per_kg_h2":
        yearly["cost"].sum() / yearly["h2_kg"].sum(),

    "co2_intensity_kg_per_kg_h2":
        yearly["co2_kg"].sum() / yearly["h2_kg"].sum(),

    "mean_price_on": yearly["mean_price_on"].mean(),
    "mean_price_off": yearly["mean_price_off"].mean(),

    "mean_on_duration_hr": yearly["mean_on_duration_hr"].mean(),
    "mean_off_duration_hr": yearly["mean_off_duration_hr"].mean(),

    "startups_per_year": yearly["startups"].mean(),
    "startups_total": startups_total,

    "h2_per_startup_kg": yearly["h2_per_startup_kg"].mean(),
}])


# ----------------------------------------------------
# Write CSV
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