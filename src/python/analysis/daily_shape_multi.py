import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, simpledialog

# --------------------------
# LOAD FILE
# --------------------------
root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select H5 file",
    filetypes=[("HDF5", "*.h5")]
)

f = h5py.File(file_path, 'r')

# --------------------------
# VARIABLE SELECTION
# --------------------------
datasets = {
    "0": "sim/P_grid_kW",
    "1": "sim/h2_kgph",
    "2": "sim/cost",
    "3": "emissions/co2_kg_per_timestep"
}

menu = "Select dataset:\n\n"
for k, v in datasets.items():
    menu += f"{k}: {v}\n"

choice = simpledialog.askstring("Variable", menu)

if choice not in datasets:
    raise ValueError("Invalid selection")

var_path = datasets[choice]
data = f[var_path]

print(f"Selected: {var_path}")

# --------------------------
# SAMPLE SIZE (NEW)
# --------------------------
n_total = data.shape[1]

N = simpledialog.askinteger(
    "Sample Configurations",
    f"Enter number of configurations to sample (max {n_total}):"
)

if N is None or N <= 0:
    raise ValueError("Invalid sample size")

seed = simpledialog.askinteger(
    "Random Seed (optional)",
    "Enter seed for reproducibility or cancel:"
)

if seed is not None:
    np.random.seed(seed)

if N >= n_total:
    selected_idx = np.arange(n_total)
else:
    selected_idx = np.random.choice(n_total, size=N, replace=False)

print(f"Using {len(selected_idx)} configurations")

# --------------------------
# GROUP + PLOT MODES
# --------------------------
group_mode = simpledialog.askinteger(
    "Grouping Mode",
    "0: Full Year\n1: Monthly\n2: Seasonal"
)

plot_mode = simpledialog.askinteger(
    "Plot Mode",
    "0: Mean Shape\n1: ON Probability\n2: Percentiles\n3: Heatmap"
)

# --------------------------
# TIME PROCESSING
# --------------------------
time = f['time'][0]
time = pd.to_datetime(time, unit='s', origin='unix')  # adjust if needed

df_time = pd.DataFrame({"time": time})
df_time['month'] = df_time['time'].dt.month
df_time['date'] = df_time['time'].dt.date
df_time['step'] = df_time.groupby('date').cumcount()

def get_season(month):
    if month in [12,1,2]:
        return "Winter"
    elif month in [3,4,5]:
        return "Spring"
    elif month in [6,7,8]:
        return "Summer"
    else:
        return "Fall"

df_time['season'] = df_time['month'].apply(get_season)

# Keep full days only
valid_days = df_time.groupby('date').size()
valid_days = valid_days[valid_days == 96].index
df_time = df_time[df_time['date'].isin(valid_days)]

# --------------------------
# BUILD GROUPS
# --------------------------
groups = {}

if group_mode == 0:
    groups["Full Year"] = df_time

elif group_mode == 1:
    for m in range(1, 13):
        g = df_time[df_time['month'] == m]
        if len(g) > 0:
            groups[f"Month {m}"] = g

elif group_mode == 2:
    for s in ["Winter", "Spring", "Summer", "Fall"]:
        g = df_time[df_time['season'] == s]
        if len(g) > 0:
            groups[s] = g

# --------------------------
# ANALYSIS FUNCTION
# --------------------------
def analyze_group(df_subset):

    profiles = []
    idx = df_subset.index

    for i in selected_idx:

        series = data[:, i]
        series = series[idx]

        df_tmp = df_subset.copy()
        df_tmp['val'] = series

        daily_profiles = []

        for _, g in df_tmp.groupby('date'):
            if len(g) == 96:
                daily_profiles.append(g.sort_values('step')['val'].values)

        if len(daily_profiles) == 0:
            continue

        daily_profiles = np.array(daily_profiles)

        # average daily shape per configuration
        profile = np.mean(daily_profiles, axis=0)

        profiles.append(profile)

    if len(profiles) == 0:
        return None

    return np.array(profiles)

# --------------------------
# PLOTTING
# --------------------------
time_axis = pd.date_range("00:00", periods=96, freq="15min")

plt.figure(figsize=(12,6))

for label, df_group in groups.items():

    result = analyze_group(df_group)

    if result is None:
        continue

    if plot_mode == 0:
        # Mean normalized shape
        mean = np.mean(result, axis=0)
        shape = (mean - np.min(mean)) / (np.max(mean) - np.min(mean))
        plt.plot(time_axis, shape, label=label)

    elif plot_mode == 1:
        # ON probability
        prob = np.mean(result > 0, axis=0)
        plt.plot(time_axis, prob, label=label)

    elif plot_mode == 2:
        # Percentiles
        p10 = np.percentile(result, 10, axis=0)
        p50 = np.percentile(result, 50, axis=0)
        p90 = np.percentile(result, 90, axis=0)

        plt.plot(time_axis, p50, label=f"{label} median")
        plt.fill_between(time_axis, p10, p90, alpha=0.2)

    elif plot_mode == 3:
        # Heatmap (only show first group for readability)
        plt.figure(figsize=(10,6))
        plt.imshow(result, aspect='auto', cmap='viridis')
        plt.colorbar(label=var_path)
        plt.title(f"Heatmap: {label}")
        plt.xlabel("Time Step")
        plt.ylabel("Configuration Index")
        plt.show()
        break

# --------------------------
# FINAL FORMAT
# --------------------------
if plot_mode in [0,1,2]:

    plt.xticks(rotation=45)
    plt.xlabel("Time of Day")

    if plot_mode == 0:
        plt.ylabel("Normalized Shape (0–1)")
        plt.title("Average Shape Across Configurations")

    elif plot_mode == 1:
        plt.ylabel("Probability")
        plt.title("ON Probability Across Configurations")

    elif plot_mode == 2:
        plt.ylabel("Value")
        plt.title("Percentile Bands Across Configurations")

    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()