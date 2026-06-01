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
# Safe division helper
# ----------------------------------------------------
def safe_div(num, denom, fill=np.nan):
    """Return num/denom, or fill wherever denom is zero."""
    num   = np.asarray(num,   dtype=float)
    denom = np.asarray(denom, dtype=float)
    return np.where(denom != 0, num / denom, fill)


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
h5_file  = PROJECT_ROOT / "outputs" / "results" / "clean_case.h5"
csv_file = PROJECT_ROOT / "outputs" / "tables"  / "clean_case.csv"
price_file = PROJECT_ROOT / "data" / "inputs" / "price.txt"


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

    startups_total = int(f["/state/startups"][0].item())


# ----------------------------------------------------
# Timestep duration
# ----------------------------------------------------
dt_hr = (time[1] - time[0]).total_seconds() / 3600.0


# ----------------------------------------------------
# Build base DataFrame
# ----------------------------------------------------
df_ts = pd.DataFrame({
    "time":      time,
    "P_grid_kW": P_grid_kW,
    "h2_kgph":   h2_kgph,
    "cost_signal": cost_ts,
    "co2_kg":    co2_ts,
})


# ----------------------------------------------------
# Load and align price data by timestamp
# ----------------------------------------------------
price_df = pd.read_csv(price_file)
price_df["time"] = pd.to_datetime(price_df["Timestamp"])
price_df = price_df.rename(columns={"Price": "price_per_MWh"})

df_ts = df_ts.merge(price_df[["time", "price_per_MWh"]], on="time", how="left")

if df_ts["price_per_MWh"].isna().any():
    missing_frac = df_ts["price_per_MWh"].isna().mean()
    raise ValueError(
        f"Price alignment failed: {missing_frac:.2%} of timesteps missing price data"
    )


# ----------------------------------------------------
# Derived columns
# ----------------------------------------------------
df_ts["year"]       = df_ts["time"].dt.year
df_ts["energy_MWh"] = df_ts["P_grid_kW"] * dt_hr / 1000
df_ts["h2_kg"]      = df_ts["h2_kgph"] * dt_hr
df_ts["operating"]  = df_ts["P_grid_kW"] > 0
df_ts["cost_$"]     = df_ts["energy_MWh"] * df_ts["price_per_MWh"]

# co2 per kg h2 — zero-safe
df_ts["co2_per_h2"] = safe_div(df_ts["co2_kg"].values,
                                df_ts["h2_kg"].values,
                                fill=0.0)


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
# Price metrics
# ----------------------------------------------------
def year_price_metrics(g):
    on_mask  = g["operating"]
    off_mask = ~g["operating"]

    weights = g.loc[on_mask, "energy_MWh"].values
    prices  = g.loc[on_mask, "price_per_MWh"].values

    # weighted mean price when ON — safe against zero total weight
    if on_mask.any() and weights.sum() > 0:
        mean_on = np.average(prices, weights=weights)
    else:
        mean_on = np.nan

    mean_off = g.loc[off_mask, "price_per_MWh"].mean() \
               if off_mask.any() else np.nan

    return pd.Series({"mean_price_on": mean_on, "mean_price_off": mean_off})

price_metrics = (
    df_ts
    .groupby("year")
    .apply(year_price_metrics)
    .reset_index()
)


# ----------------------------------------------------
# Duration + startup metrics
# ----------------------------------------------------
def year_duration_metrics(g):
    on_runs  = g.loc[g["operating"]]
    off_runs = g.loc[~g["operating"]]
    n_starts = int(g["operating"].sum())

    return pd.Series({
        "mean_on_duration_hr":  on_runs["duration_hr"].mean()
                                if not on_runs.empty else np.nan,
        "mean_off_duration_hr": off_runs["duration_hr"].mean()
                                if not off_runs.empty else np.nan,
        "startups":             n_starts,
        "h2_per_startup_kg":    safe_div(on_runs["h2_kg"].sum(),
                                         n_starts, fill=0.0).item(),
    })

duration_metrics = (
    run_tbl
    .groupby("year")
    .apply(year_duration_metrics)
    .reset_index()
)


# ----------------------------------------------------
# Yearly aggregation
# ----------------------------------------------------
P_rated_kW = df_ts["P_grid_kW"].max()  # may be 0 if system never ran

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

yearly["capacity_factor"] = safe_div(
    yearly["energy_MWh"].values,
    P_rated_kW * yearly["hours"].values / 1000,
    fill=0.0
)

yearly["utilization_rate"] = safe_div(
    yearly["operating_hours"].values,
    yearly["total_steps"].values,
    fill=0.0
)

yearly["cost_per_kg_h2"] = safe_div(
    yearly["cost"].values,
    yearly["h2_kg"].values,
    fill=np.nan
)

yearly["co2_intensity_kg_per_kg_h2"] = safe_div(
    yearly["co2_kg"].values,
    yearly["h2_kg"].values,
    fill=np.nan
)


# ----------------------------------------------------
# Merge metrics
# ----------------------------------------------------
yearly = (
    yearly
    .merge(price_metrics,    on="year", how="left")
    .merge(duration_metrics, on="year", how="left")
)


# ----------------------------------------------------
# Totals
# ----------------------------------------------------
total_hours   = yearly["hours"].sum()
total_h2_kg   = yearly["h2_kg"].sum()
total_energy  = yearly["energy_MWh"].sum()
total_cost    = yearly["cost"].sum()
total_co2     = yearly["co2_kg"].sum()

weighted_utilization = (
    np.average(yearly["utilization_rate"], weights=yearly["hours"])
    if yearly["hours"].sum() > 0 else np.nan
)

totals = pd.DataFrame([{
    "h2_kg":                     total_h2_kg,
    "co2_kg":                    total_co2,
    "energy_MWh":                total_energy,
    "cost":                      total_cost,
    "capacity_factor":           safe_div(total_energy,
                                          P_rated_kW * total_hours / 1000,
                                          fill=0.0).item(),
    "utilization_rate":          weighted_utilization,
    "cost_per_kg_h2":            safe_div(total_cost,   total_h2_kg, fill=np.nan).item(),
    "co2_intensity_kg_per_kg_h2":safe_div(total_co2,    total_h2_kg, fill=np.nan).item(),
    "mean_price_on":             yearly["mean_price_on"].mean(),
    "mean_price_off":            yearly["mean_price_off"].mean(),
    "mean_on_duration_hr":       yearly["mean_on_duration_hr"].mean(),
    "mean_off_duration_hr":      yearly["mean_off_duration_hr"].mean(),
    "startups_per_year":         yearly["startups"].mean(),
    "startups_total":            startups_total,
    "h2_per_startup_kg":         yearly["h2_per_startup_kg"].mean(),
}])


# ----------------------------------------------------
# Write CSV
# ----------------------------------------------------
csv_file.parent.mkdir(parents=True, exist_ok=True)

with open(csv_file, "w", newline="") as f:
    f.write("# --- totals ---\n")
    totals.to_csv(f, index=False)

    f.write("\n# --- yearly_metrics ---\n")
    yearly.to_csv(f, index=False)

    f.write("\n# --- time_series ---\n")
    df_ts.drop(columns=["year"]).to_csv(f, index=False)

print("[OK] Export complete")
print(f"     File: {csv_file}")