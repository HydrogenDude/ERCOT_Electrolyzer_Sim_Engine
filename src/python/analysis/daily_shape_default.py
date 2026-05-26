import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, simpledialog

# --------------------------
# LOAD FILE
# --------------------------
root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select data file",
    filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls")]
)

if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
else:
    df = pd.read_excel(file_path)

# --------------------------
# PREPROCESS
# --------------------------
df.columns = df.columns.str.strip()
df['time'] = pd.to_datetime(df['time'], errors='coerce')
df = df.dropna(subset=['time'])

# --------------------------
# VARIABLE SELECTION
# --------------------------
numeric_cols = [c for c in df.columns if c != 'time']

menu_text = "Select a column:\n\n"
for i, col in enumerate(numeric_cols):
    marker = " <-- recommended" if "Power" in col else ""
    menu_text += f"{i}: {col}{marker}\n"

selection = simpledialog.askinteger("Column Selection", menu_text)

if selection is None or selection < 0 or selection >= len(numeric_cols):
    raise ValueError("Invalid selection")

var = numeric_cols[selection]
print(f"Selected column: {var}")

# --------------------------
# GROUPING MODE
# --------------------------
mode = simpledialog.askinteger(
    "Grouping Mode",
    "0: All Data\n1: By Year\n2: By Month\n3: By Season"
)

# --------------------------
# PLOT TYPE
# --------------------------
plot_mode = simpledialog.askinteger(
    "Plot Type",
    "0: Mean Shape\n1: ON Probability\n2: Percentiles\n3: Heatmap"
)

# --------------------------
# TIME FEATURES
# --------------------------
df = df.sort_values('time')
df['year'] = df['time'].dt.year
df['month'] = df['time'].dt.month
df['date'] = df['time'].dt.date
df['step'] = df.groupby('date').cumcount()

def get_season(month):
    if month in [12,1,2]:
        return "Winter"
    elif month in [3,4,5]:
        return "Spring"
    elif month in [6,7,8]:
        return "Summer"
    else:
        return "Fall"

df['season'] = df['month'].apply(get_season)

# --------------------------
# FUNCTION: BUILD DAILY MATRIX
# --------------------------
def build_daily_matrix(df_subset):

    all_days = []

    for year, df_year in df_subset.groupby('year'):

        counts = df_year.groupby('date').size()
        valid_days = counts[counts == 96].index
        df_year = df_year[df_year['date'].isin(valid_days)]

        if len(df_year) == 0:
            continue

        mu = df_year[var].mean()
        sigma = df_year[var].std()

        if sigma == 0 or np.isnan(sigma):
            continue

        df_year = df_year.copy()
        df_year['z'] = (df_year[var] - mu) / sigma

        for _, df_day in df_year.groupby('date'):
            if len(df_day) == 96:
                profile = df_day.sort_values('step')['z'].values
                all_days.append(profile)

    if len(all_days) == 0:
        return None

    return np.array(all_days)

# --------------------------
# BUILD GROUPS
# --------------------------
groups = {}

if mode == 0:
    groups["All Data"] = df

elif mode == 1:
    for y, g in df.groupby('year'):
        groups[str(y)] = g

elif mode == 2:
    for m in range(1,13):
        groups[f"Month {m}"] = df[df['month'] == m]

elif mode == 3:
    for s in ["Winter","Spring","Summer","Fall"]:
        groups[s] = df[df['season'] == s]

# --------------------------
# PLOT
# --------------------------
time_axis = pd.date_range("00:00", periods=96, freq="15min")

plt.figure(figsize=(12,6))

for label, df_group in groups.items():

    data = build_daily_matrix(df_group)

    if data is None:
        continue

    if plot_mode == 0:
        # Mean shape
        mean = np.mean(data, axis=0)
        shape = (mean - np.min(mean)) / (np.max(mean) - np.min(mean))
        plt.plot(time_axis, shape, label=label)

    elif plot_mode == 1:
        # ON probability (z > 0 is not meaningful, use raw > 0)
        raw_days = []

        for d, g in df_group.groupby('date'):
            if len(g) == 96:
                raw_days.append(g.sort_values('step')[var].values)

        raw_days = np.array(raw_days)
        prob = np.mean(raw_days > 0, axis=0)

        plt.plot(time_axis, prob, label=label)

    elif plot_mode == 2:
        # Percentiles
        p10 = np.percentile(data, 10, axis=0)
        p50 = np.percentile(data, 50, axis=0)
        p90 = np.percentile(data, 90, axis=0)

        plt.plot(time_axis, p50, label=f"{label} median")
        plt.fill_between(time_axis, p10, p90, alpha=0.2)

    elif plot_mode == 3:
        # Heatmap (only plot first group)
        plt.figure(figsize=(10,6))
        plt.imshow(data, aspect='auto', cmap='viridis')
        plt.colorbar(label="Z-score")
        plt.title(f"Heatmap: {label}")
        plt.xlabel("Time Step")
        plt.ylabel("Day Index")
        plt.show()
        break

# --------------------------
# FINALIZE LINE PLOTS
# --------------------------
if plot_mode in [0,1,2]:
    plt.xticks(rotation=45)
    plt.xlabel("Time of Day")

    if plot_mode == 0:
        plt.ylabel("Normalized Shape (0–1)")
        plt.title(f"Shape: {var}")

    elif plot_mode == 1:
        plt.ylabel("Probability")
        plt.title(f"ON Probability: {var}")

    elif plot_mode == 2:
        plt.ylabel("Z-score")
        plt.title(f"Percentile Bands: {var}")

    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
