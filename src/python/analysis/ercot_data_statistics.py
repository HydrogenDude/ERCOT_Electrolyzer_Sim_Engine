import pandas as pd
import numpy as np
from pathlib import Path
import statsmodels.api as sm

# ============================================================
# SETTINGS
# ============================================================

SAVE_CSV_OUTPUTS = False   # Set to False if you do not want CSV outputs
OUTPUT_DIR_NAME = "analysis_outputs"

# ============================================================
# FIND PROJECT ROOT
# ============================================================

def find_project_root(start: Path = None) -> Path:
    """
    Walk upward from the current location until a folder containing
    data/inputs is found. That folder is treated as the project root.
    """
    if start is None:
        start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd().resolve()

    current = start
    for candidate in [current] + list(current.parents):
        if (candidate / "data" / "inputs").exists():
            return candidate

    raise FileNotFoundError(
        "Could not find project root containing 'data/inputs'."
    )

PROJECT_ROOT = find_project_root()
EXCEL_FILE = PROJECT_ROOT / "data" / "inputs" / "ERCOT_2020_2025.xlsx"
OUTPUT_DIR = PROJECT_ROOT / OUTPUT_DIR_NAME

if SAVE_CSV_OUTPUTS:
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("=" * 80)
print("ERCOT STATISTICAL ANALYSIS")
print("=" * 80)
print(f"Project root: {PROJECT_ROOT}")
print(f"Excel file:   {EXCEL_FILE}")
print()

if not EXCEL_FILE.exists():
    raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE}")

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_excel(EXCEL_FILE, sheet_name=0, engine="openpyxl")
df.columns = [str(c).strip() for c in df.columns]

rename_map = {
    "Other/BES": "Other_BES",
    "Clean Ratio": "Clean_Ratio",
    "Renewable Ratio": "Renewable_Ratio",
}
df = df.rename(columns=rename_map)

if "Time" not in df.columns:
    raise ValueError("Expected a 'Time' column in the Excel file.")

# Clean and parse time column
df["Time"] = df["Time"].astype(str).str.replace("'", "", regex=False).str.strip()
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df = df.dropna(subset=["Time"]).copy()

# ============================================================
# NUMERIC COLUMNS
# ============================================================

base_numeric_cols = [
    "Load", "Wind", "Solar", "Gas_CC", "Gas_Other", "Coal", "Nuclear",
    "Hydro", "Biomass", "Other_BES", "WSL", "Price", "Clean_Ratio", "Renewable_Ratio"
]

available_numeric_cols = [c for c in base_numeric_cols if c in df.columns]

for col in available_numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if available_numeric_cols:
    df = df.dropna(how="all", subset=available_numeric_cols).copy()

# ============================================================
# TIME FEATURES
# ============================================================

df["Year"] = df["Time"].dt.year
df["Month"] = df["Time"].dt.month
df["Month_Name"] = df["Time"].dt.month_name()
df["Day"] = df["Time"].dt.day
df["Hour"] = df["Time"].dt.hour
df["Quarter_Hour"] = df["Time"].dt.minute
df["DayOfWeek"] = df["Time"].dt.day_name()

# ============================================================
# DERIVED METRICS
# ============================================================

# Net load
if all(c in df.columns for c in ["Load", "Wind", "Solar"]):
    df["Net_Load"] = df["Load"] - df["Wind"] - df["Solar"]

# Total generation
generation_cols = [
    c for c in ["Wind", "Solar", "Gas_CC", "Gas_Other", "Coal", "Nuclear", "Hydro", "Biomass", "Other_BES"]
    if c in df.columns
]
if generation_cols:
    df["Total_Generation"] = df[generation_cols].sum(axis=1)

# Renewable generation
renewable_cols = [c for c in ["Wind", "Solar", "Hydro", "Biomass"] if c in df.columns]
if renewable_cols:
    df["Renewable_Generation"] = df[renewable_cols].sum(axis=1)

# Clean generation
clean_cols = [c for c in ["Wind", "Solar", "Hydro", "Biomass", "Nuclear"] if c in df.columns]
if clean_cols:
    df["Clean_Generation"] = df[clean_cols].sum(axis=1)

# Derive Renewable_Ratio if missing
if "Renewable_Ratio" not in df.columns:
    if "Renewable_Generation" in df.columns and "Total_Generation" in df.columns:
        df["Renewable_Ratio"] = np.where(
            df["Total_Generation"] != 0,
            df["Renewable_Generation"] / df["Total_Generation"],
            np.nan
        )

# Derive Clean_Ratio if missing
if "Clean_Ratio" not in df.columns:
    if "Clean_Generation" in df.columns and "Total_Generation" in df.columns:
        df["Clean_Ratio"] = np.where(
            df["Total_Generation"] != 0,
            df["Clean_Generation"] / df["Total_Generation"],
            np.nan
        )

analysis_cols = [
    c for c in [
        "Load", "Wind", "Solar", "Gas_CC", "Gas_Other", "Coal", "Nuclear",
        "Hydro", "Biomass", "Other_BES", "WSL", "Price",
        "Net_Load", "Total_Generation", "Renewable_Generation", "Clean_Generation",
        "Renewable_Ratio", "Clean_Ratio"
    ] if c in df.columns
]

# ============================================================
# BASIC DATASET SUMMARY
# ============================================================

print("DATASET SUMMARY")
print("-" * 80)
print(f"Rows analyzed:    {len(df):,}")
print(f"Columns analyzed: {len(df.columns)}")
print(f"Time range:       {df['Time'].min()}  -->  {df['Time'].max()}")
print()
print("Analysis columns:")
print(", ".join(analysis_cols))
print()

# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

desc_stats = df[analysis_cols].describe().T
desc_stats["median"] = df[analysis_cols].median()
desc_stats["skew"] = df[analysis_cols].skew()
desc_stats["kurtosis"] = df[analysis_cols].kurtosis()

desc_display = desc_stats[["mean", "std", "min", "25%", "50%", "75%", "max", "median", "skew", "kurtosis"]]

print("DESCRIPTIVE STATISTICS")
print("-" * 80)
print(desc_display.round(4).to_string())
print()

# ============================================================
# CORRELATION MATRIX
# ============================================================

corr_matrix = df[analysis_cols].corr(method="pearson")

print("CORRELATION MATRIX")
print("-" * 80)
print(corr_matrix.round(4).to_string())
print()

# ============================================================
# CORRELATIONS WITH PRICE
# ============================================================

if "Price" in df.columns:
    price_corr = {}
    for col in analysis_cols:
        if col != "Price":
            valid = df[[col, "Price"]].dropna()
            if len(valid) > 2:
                price_corr[col] = valid[col].corr(valid["Price"])

    price_corr_df = pd.DataFrame.from_dict(
        price_corr, orient="index", columns=["corr_with_price"]
    ).sort_values("corr_with_price", ascending=False)

    print("CORRELATIONS WITH PRICE")
    print("-" * 80)
    print(price_corr_df.round(4).to_string())
    print()

# ============================================================
# HOURLY AVERAGES
# ============================================================

hourly_avg = df.groupby("Hour")[analysis_cols].mean(numeric_only=True)

print("HOURLY AVERAGES (first 24 rows)")
print("-" * 80)
print(hourly_avg.round(4).to_string())
print()

# ============================================================
# MONTHLY AVERAGES
# ============================================================

monthly_avg = df.groupby(["Year", "Month"])[analysis_cols].mean(numeric_only=True)

print("MONTHLY AVERAGES")
print("-" * 80)
print(monthly_avg.round(4).to_string())
print()

# ============================================================
# EXTREME VALUE SUMMARY
# ============================================================

extreme_vars = [c for c in ["Load", "Wind", "Solar", "Price", "Net_Load", "Clean_Ratio", "Renewable_Ratio"] if c in df.columns]
extreme_summary = []

for col in extreme_vars:
    s = df[col].dropna()
    if len(s) > 0:
        extreme_summary.append({
            "variable": col,
            "min": s.min(),
            "p01": s.quantile(0.01),
            "p05": s.quantile(0.05),
            "median": s.median(),
            "p95": s.quantile(0.95),
            "p99": s.quantile(0.99),
            "max": s.max()
        })

extreme_summary_df = pd.DataFrame(extreme_summary)

print("EXTREME VALUE SUMMARY")
print("-" * 80)
print(extreme_summary_df.round(4).to_string(index=False))
print()

# ============================================================
# BALANCE CHECK
# ============================================================

if "Load" in df.columns and "Total_Generation" in df.columns:
    df["Generation_Minus_Load"] = df["Total_Generation"] - df["Load"]
    print("GENERATION MINUS LOAD SUMMARY")
    print("-" * 80)
    print(df["Generation_Minus_Load"].describe().round(4).to_string())
    print()

# ============================================================
# REGRESSION A: Price ~ Load + Wind + Solar
# ============================================================

regA_predictors = [c for c in ["Load", "Wind", "Solar"] if c in df.columns]
if "Price" in df.columns and len(regA_predictors) > 0:
    regA_df = df[["Price"] + regA_predictors].dropna().copy()
    X = sm.add_constant(regA_df[regA_predictors])
    y = regA_df["Price"]
    modelA = sm.OLS(y, X).fit()

    print("REGRESSION A: Price ~ Load + Wind + Solar")
    print("-" * 80)
    print(modelA.summary())
    print()

# ============================================================
# REGRESSION B: Price ~ Load + Clean_Ratio + Renewable_Ratio
# ============================================================

regB_predictors = [c for c in ["Load", "Clean_Ratio", "Renewable_Ratio"] if c in df.columns]
if "Price" in df.columns and len(regB_predictors) >= 2:
    regB_df = df[["Price"] + regB_predictors].dropna().copy()
    X = sm.add_constant(regB_df[regB_predictors])
    y = regB_df["Price"]
    modelB = sm.OLS(y, X).fit()

    print("REGRESSION B: Price ~ Load + Clean_Ratio + Renewable_Ratio")
    print("-" * 80)
    print(modelB.summary())
    print()

# ============================================================
# OPTIONAL CSV OUTPUTS
# ============================================================

if SAVE_CSV_OUTPUTS:
    desc_stats.to_csv(OUTPUT_DIR / "descriptive_statistics.csv")
    corr_matrix.to_csv(OUTPUT_DIR / "correlation_matrix.csv")
    hourly_avg.to_csv(OUTPUT_DIR / "hourly_averages.csv")
    monthly_avg.to_csv(OUTPUT_DIR / "monthly_averages.csv")
    extreme_summary_df.to_csv(OUTPUT_DIR / "extreme_value_summary.csv", index=False)

    if "Price" in df.columns:
        price_corr_df.to_csv(OUTPUT_DIR / "price_correlations.csv")

    df.to_csv(OUTPUT_DIR / "cleaned_dataset.csv", index=False)

    print("CSV outputs were also saved to:")
    print(OUTPUT_DIR)
    print()

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)