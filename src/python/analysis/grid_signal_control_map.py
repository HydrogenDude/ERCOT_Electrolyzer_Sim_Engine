import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np
import matplotlib.colors as mcolors
import tkinter as tk
from tkinter import filedialog

# ==================================================
# SETTINGS (NEW)
# ==================================================

ENABLE_SMOOTHING = False
SMOOTH_WINDOW_DAYS = 2
TIME_STEP_MIN = 15  # minutes

# ==================================================
# CONTROL PARAMETERS
# ==================================================

clean_turndown = 0.50
clean_stop = 0.40

price_turndown = 50
price_stop = 55

# ==================================================
# PROJECT ROOT
# ==================================================

def get_project_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# ==================================================
# FILE PICKER
# ==================================================

def select_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        initialdir=PROJECT_ROOT / "outputs" / "tables",
        title="Select timeseries file",
        filetypes=[("CSV files", "*.csv")]
    )

    return Path(path) if path else None

# ==================================================
# LOAD DATA
# ==================================================

def load_data(path):
    df = pd.read_csv(path)

    df.columns = df.columns.str.strip()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    df = df.dropna(subset=["time"])
    df = df.sort_values("time").reset_index(drop=True)

    return df

# ==================================================
# NORMALIZATION FUNCTIONS
# ==================================================

def normalize_clean(values):
    vals = values.copy()
    norm = np.zeros_like(vals, dtype=float)

    mask1 = vals <= clean_stop
    norm[mask1] = 0.0

    mask2 = (vals > clean_stop) & (vals <= clean_turndown)
    norm[mask2] = (vals[mask2] - clean_stop) / (clean_turndown - clean_stop) * 0.5

    mask3 = vals > clean_turndown
    norm[mask3] = 0.5 + (vals[mask3] - clean_turndown) / (1 - clean_turndown) * 0.5

    return np.clip(norm, 0, 1)


def normalize_price(values):
    vals = values.copy()
    norm = np.zeros_like(vals, dtype=float)

    mask1 = vals >= price_stop
    norm[mask1] = 0.0

    mask2 = (vals >= price_turndown) & (vals < price_stop)
    norm[mask2] = 0.5 - (vals[mask2] - price_turndown) / (price_stop - price_turndown) * 0.5

    mask3 = vals < price_turndown
    norm[mask3] = 0.5 + (price_turndown - vals[mask3]) / price_turndown * 0.5

    return np.clip(norm, 0, 1)

# ==================================================
# SMOOTHING (NEW)
# ==================================================

def get_window_size(days):
    steps_per_day = int(24 * 60 / TIME_STEP_MIN)
    return days * steps_per_day


def smooth_series(values, window):
    return pd.Series(values).rolling(
        window=window,
        center=True,
        min_periods=1
    ).mean().values

# ==================================================
# COLORMAP
# ==================================================

cmap = mcolors.LinearSegmentedColormap.from_list(
    "control_cmap",
    [
        (0.0, "red"),
        (0.5, "yellow"),
        (1.0, "green")
    ]
)

# ==================================================
# PLOT FUNCTION
# ==================================================

def plot_heatmap(time, norm_vals, ylabel):

    fig, ax = plt.subplots(figsize=(12, 1))

    t_vals = mdates.date2num(time)

    norm_vals = np.clip(norm_vals, 0.0, 1.0)
    img = np.expand_dims(norm_vals, axis=0)

    ax.imshow(
        img,
        aspect='auto',
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        extent=[t_vals[0], t_vals[-1], 0, 1],
        interpolation='nearest'
    )

    # AXIS FORMATTING
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(t_vals[0], t_vals[-1])

    plt.tight_layout()
    plt.subplots_adjust(left=0.059)
    plt.show()

# ==================================================
# MAIN
# ==================================================

def run():

    path = select_file()
    if not path:
        print("No file selected.")
        return

    df = load_data(path)

    # Normalize
    clean_norm = normalize_clean(df["clean_ratio"].values)
    price_norm = normalize_price(df["energy_price"].values)

    # ✅ Apply smoothing if enabled
    if ENABLE_SMOOTHING:
        window = get_window_size(SMOOTH_WINDOW_DAYS)

        clean_norm = smooth_series(clean_norm, window)
        price_norm = smooth_series(price_norm, window)

    # Plot
    plot_heatmap(df["time"], clean_norm, "CR")
    plot_heatmap(df["time"], price_norm, "$/MWh")

# ==================================================
# ENTRY
# ==================================================

if __name__ == "__main__":
    run()