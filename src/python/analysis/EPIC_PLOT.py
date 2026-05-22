import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np
import matplotlib.colors as mcolors
import tkinter as tk
from tkinter import filedialog

# ==================================================
# CONFIGURATION
# ==================================================

PLOT_CONFIG = {
    "axis_label_size": 12,
    "tick_label_size": 10,
    "legend_size": 10,
}

PLOTS = [
    {
        "col1": "System Power (kW)",
        "col2": "System Power Avg (kW)",
        "label1": "15-min",
        "label2": "14-day avg",
        "ylabel": "Power (kW)"
    },
]

# ==================================================
# CONTROL PARAMETERS
# ==================================================

clean_turndown = 0.50
clean_stop = 0.40

price_turndown = 50
price_stop = 55

# ==================================================
# PROJECT ROOT + FILE PICKER
# ==================================================

def get_project_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

def select_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        initialdir=PROJECT_ROOT / "outputs" / "tables",
        title="Select timeseries file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
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
# NORMALIZATION
# ==================================================

def normalize_clean(vals):
    norm = np.zeros_like(vals, dtype=float)

    norm[vals <= clean_stop] = 0.0

    mask = (vals > clean_stop) & (vals <= clean_turndown)
    norm[mask] = (vals[mask] - clean_stop) / (clean_turndown - clean_stop) * 0.5

    mask = vals > clean_turndown
    norm[mask] = 0.5 + (vals[mask] - clean_turndown) / (1 - clean_turndown) * 0.5

    return np.clip(norm, 0, 1)


def normalize_price(vals):
    norm = np.zeros_like(vals, dtype=float)

    norm[vals >= price_stop] = 0.0

    mask = (vals >= price_turndown) & (vals < price_stop)
    norm[mask] = 0.5 - (vals[mask] - price_turndown) / (price_stop - price_turndown) * 0.5

    mask = vals < price_turndown
    norm[mask] = 0.5 + (price_turndown - vals[mask]) / price_turndown * 0.5

    return np.clip(norm, 0, 1)

# ==================================================
# COLORMAP
# ==================================================

cmap = mcolors.LinearSegmentedColormap.from_list(
    "control_cmap",
    [(0.0, "red"), (0.5, "yellow"), (1.0, "green")]
)

# ==================================================
# COMBINED PLOT
# ==================================================

def plot_combined(df, cfg):

    time = df["time"]
    t_vals = mdates.date2num(time)

    clean_norm = normalize_clean(df["clean_ratio"].values)
    price_norm = normalize_price(df["energy_price"].values)

    fig, axes = plt.subplots(
        3, 1,
        figsize=(12, 5),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 0.6, 0.6]}
    )

    # ✅ VERY tight stacking
    fig.subplots_adjust(hspace=0.05)

    # ==================================================
    # TOP: POWER
    # ==================================================
    ax = axes[0]

    line1, = ax.plot(time, df[cfg["col1"]],
                     color="blue", alpha=0.3, linewidth=0.5)

    line2, = ax.plot(time, df[cfg["col2"]],
                     color="orange", linewidth=1.8)

    ax.set_ylabel(cfg["ylabel"], fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_ylim(0, 80)
    ax.grid(True, alpha=0.25)

    # ✅ Legend with consistent linewidth
    legend = ax.legend(
        [line1, line2],
        [cfg["label1"], cfg["label2"]],
        fontsize=PLOT_CONFIG["legend_size"],
        loc="upper right"
    )
    for legline in legend.legend_handles:
        legline.set_linewidth(1.5)

    # ==================================================
    # MIDDLE: CR
    # ==================================================
    ax = axes[1]

    img = np.expand_dims(clean_norm, axis=0)
    ax.imshow(img, aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])

    ax.set_ylabel("CR", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])

    # ✅ Force full vertical fill
    ax.set_ylim(0, 1)

    # ==================================================
    # BOTTOM: PRICE
    # ==================================================
    ax = axes[2]

    img = np.expand_dims(price_norm, axis=0)
    ax.imshow(img, aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])

    ax.set_ylabel("$/MWh", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])
    ax.set_ylim(0, 1)

    # ==================================================
    # SHARED X AXIS
    # ==================================================
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # ==================================================
    # CLEAN STACKING FIXES
    # ==================================================
    for ax in axes:
        ax.tick_params(labelsize=PLOT_CONFIG["tick_label_size"])
        ax.margins(x=0, y=0)

    # ✅ Remove x labels from upper plots
    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)

    for ax in axes[:2]:
        ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

    fig.subplots_adjust(
        left=0.06,
        right=0.995,
        top=0.98,
        bottom=0.08,
        hspace=0.02
    )

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

    for cfg in PLOTS:
        plot_combined(df, cfg)

# ==================================================
# ENTRY
# ==================================================

if __name__ == "__main__":
    run()