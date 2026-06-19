import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import linregress

# ==================================================
# SETTINGS
# ==================================================

DT_HR = 0.25                    # 15-min timestep
H2_VALID_THRESHOLD = 1e-6       # kg, minimum H2 produced for a timestep to count
SMR_LOW, SMR_HIGH = 11.0, 14.0  # kg CO2 / kg H2, grey SMR benchmark band
N_COST_BINS = 5                 # quantile bins for the dispersion table
MIN_BIN_COUNT = 20              # minimum timesteps required to report a bin

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

if np.max(time_raw) > 1e9:
    time = pd.to_datetime(time_raw, unit="s")
else:
    raise ValueError("Unexpected time format")

years = time.year.values
unique_years = np.unique(years)

# ==================================================
# DERIVED PER-KG METRICS
# ==================================================

h2_kg = h2_rate * DT_HR
valid = h2_kg > H2_VALID_THRESHOLD

co2_per_h2 = np.full(co2.shape, np.nan, dtype=float)
cost_per_h2 = np.full(cost.shape, np.nan, dtype=float)
co2_per_h2[valid] = co2[valid] / h2_kg[valid]
cost_per_h2[valid] = cost[valid] / h2_kg[valid]

total_intensity = np.sum(co2[valid]) / np.sum(h2_kg[valid])
print(f"Overall operational CO2 intensity: {total_intensity:.2f} kg/kg "
      f"({int(np.sum(valid))} valid timesteps)\n")

# ==================================================
# 1. PER-YEAR REGRESSION: CO2/H2 ~ cost/H2
# ==================================================

reg_rows = []
for y in unique_years:
    mask = valid & (years == y)
    n = int(np.sum(mask))
    if n < 2:
        reg_rows.append([str(y), n, np.nan, np.nan, np.nan])
        continue
    slope, intercept, r, p, se = linregress(cost_per_h2[mask], co2_per_h2[mask])
    reg_rows.append([str(y), n, slope, intercept, r ** 2])

slope_all, intercept_all, r_all, p_all, se_all = linregress(
    cost_per_h2[valid], co2_per_h2[valid]
)
reg_rows.append(["All (2020-2025)", int(np.sum(valid)), slope_all, intercept_all, r_all ** 2])

reg_df = pd.DataFrame(
    reg_rows,
    columns=["Year", "n", "Slope (kgCO2/kgH2 per USD/kgH2)", "Intercept", "R2"],
)

# ==================================================
# 2. FRACTION OF TIMESTEPS AT/BELOW GREY SMR BENCHMARK
# ==================================================

smr_rows = []
for y in unique_years:
    mask = valid & (years == y)
    n = int(np.sum(mask))
    if n == 0:
        smr_rows.append([str(y), n, np.nan, np.nan])
        continue
    frac_at_or_below = float(np.mean(co2_per_h2[mask] <= SMR_HIGH)) * 100
    frac_within_band = float(np.mean(
        (co2_per_h2[mask] >= SMR_LOW) & (co2_per_h2[mask] <= SMR_HIGH)
    )) * 100
    smr_rows.append([str(y), n, frac_at_or_below, frac_within_band])

smr_df = pd.DataFrame(
    smr_rows,
    columns=["Year", "n", "% <= SMR upper bound (14)", "% within SMR band (11-14)"],
)

# ==================================================
# 3. CONDITIONAL DISPERSION ACROSS FIXED COST BINS
# ==================================================
# Bin edges are computed once from the full 2020-2025 dataset so that bins
# are directly comparable across years. IQR of CO2/H2 within each bin
# shrinking over time is the quantitative version of "narrows."

bin_edges = np.unique(np.quantile(cost_per_h2[valid], np.linspace(0, 1, N_COST_BINS + 1)))
n_bins = len(bin_edges) - 1
bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}" for i in range(n_bins)]

cost_bin_idx = np.full(cost_per_h2.shape, -1, dtype=int)
cost_bin_idx[valid] = np.digitize(cost_per_h2[valid], bin_edges[1:-1], right=True)

disp_rows = []
for y in unique_years:
    row = {"Year": str(y)}
    for b, label in enumerate(bin_labels):
        mask = valid & (years == y) & (cost_bin_idx == b)
        n = int(np.sum(mask))
        if n < MIN_BIN_COUNT:
            row[label] = np.nan
        else:
            q75, q25 = np.percentile(co2_per_h2[mask], [75, 25])
            row[label] = q75 - q25
    disp_rows.append(row)

disp_df = pd.DataFrame(disp_rows).set_index("Year")

# ==================================================
# PRINT TABLES
# ==================================================

pd.set_option("display.width", 120)

def fmt(df, decimals=3):
    return df.to_string(
        index=False,
        float_format=lambda v: f"{v:,.{decimals}f}" if pd.notna(v) else "NaN",
    )

print("=" * 78)
print("TABLE 1: Per-year regression of CO2/H2 on cost/H2")
print("=" * 78)
print(fmt(reg_df))

print("\n" + "=" * 78)
print(f"TABLE 2: Share of timesteps at/below grey SMR benchmark "
      f"({SMR_LOW:.0f}-{SMR_HIGH:.0f} kg CO2/kg H2)")
print("=" * 78)
print(fmt(smr_df))

print("\n" + "=" * 78)
print("TABLE 3: IQR of CO2/H2 (kg/kg) within fixed cost bins, by year")
print(f"(cost bins in USD/kg H2; NaN where n < {MIN_BIN_COUNT})")
print("=" * 78)
print(disp_df.to_string(float_format=lambda v: f"{v:,.3f}" if pd.notna(v) else "NaN"))

print("\nDone.\n")