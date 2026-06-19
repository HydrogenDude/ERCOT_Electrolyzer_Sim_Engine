import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
from pathlib import Path
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
# ZOOM WINDOW
# ==================================================

zoom_start = "2025-04-16"
zoom_end = "2025-04-21"

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

    # --- GREEN plateau (≥ START) ---
    norm[vals >= 0.60] = 1.0

    # --- GREEN → YELLOW (START → TURNDOWN) ---
    mask1 = (vals < 0.60) & (vals >= 0.50)
    norm[mask1] = 0.5 + (vals[mask1] - 0.50) / (0.60 - 0.50) * 0.5

    # --- YELLOW → RED (TURNDOWN → STOP) ---
    mask2 = (vals < 0.50) & (vals > 0.40)
    norm[mask2] = (vals[mask2] - 0.40) / (0.50 - 0.40) * 0.5

    # --- RED plateau (≤ STOP) ---
    norm[vals <= 0.40] = 0.0

    return np.clip(norm, 0, 1)


def normalize_price(vals):
    norm = np.zeros_like(vals, dtype=float)

    # Solid green
    norm[vals <= 30] = 1.0

    # Rapid drop to yellow, then gradual to red
    mask = (vals > 30) & (vals < 55)

    x = (vals[mask] - 30) / (55 - 30)

    # Apply nonlinear curve (key change)
    norm[mask] = 1.0 - x**0.5

    # Solid red
    norm[vals >= 55] = 0.0

    return np.clip(norm, 0, 1)



# ==================================================
# COLORMAP
# ==================================================

cmap = mcolors.LinearSegmentedColormap.from_list(
    "control_cmap",
    [(0.0, "red"), (0.5, "yellow"), (1.0, "green")]
)


# ==================================================
# PLOTTING
# ==================================================

def plot_combined(df, cfg):

    time = df["time"]
    t_vals = mdates.date2num(time)

    clean_norm = normalize_clean(df["clean_ratio"].values)
    price_norm = normalize_price(df["energy_price"].values)

    fig = plt.figure(figsize=(12, 5))

    gs = gridspec.GridSpec(
        3, 2,
        width_ratios=[12, 3],
        height_ratios=[3, 0.6, 0.6]
    )

    axes_main = [fig.add_subplot(gs[i, 0]) for i in range(3)]
    axes_zoom = [fig.add_subplot(gs[i, 1], sharey=axes_main[i]) for i in range(3)]

    fig.subplots_adjust(hspace=0.05, wspace=0.05)

    zoom_mask = (time >= zoom_start) & (time <= zoom_end)
    time_zoom = time[zoom_mask]
    t_zoom_vals = mdates.date2num(time_zoom)

    x0, x1 = t_zoom_vals[0], t_zoom_vals[-1]

    # ----------------------
    # POWER (MAIN)
    # ----------------------
    ax = axes_main[0]

    line1, = ax.plot(time, df[cfg["col1"]],
                     color="blue", alpha=0.3, linewidth=0.1, zorder=1)

    line2, = ax.plot(time, df[cfg["col2"]],
                     color="orange", linewidth=1.5, zorder=2)

    ax.fill_between(time, df[cfg["col2"]], 0,
                    color="orange", alpha=0.75, linewidth=0, zorder=3)

    ax.set_ylabel(cfg["ylabel"], fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_ylim(0, 80)
    ax.grid(True, alpha=0.25)

    leg = ax.legend(
        [line1, line2],
        [cfg["label1"], cfg["label2"]],
        fontsize=PLOT_CONFIG["legend_size"],
        loc="upper right"
    )

    for legline in leg.get_lines():
        legline.set_linewidth(1.8)

    # ----------------------
    # CLEAN RATIO (MAIN)
    # ----------------------
    ax = axes_main[1]
    ax.imshow(np.expand_dims(clean_norm, axis=0),
              aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])

    ax.set_ylabel("CER", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])
    ax.set_ylim(0, 1)

    # ----------------------
    # PRICE (MAIN)
    # ----------------------
    ax = axes_main[2]
    ax.imshow(np.expand_dims(price_norm, axis=0),
              aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])

    ax.set_ylabel("$/MWh", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])
    ax.set_ylim(0, 1)

    # ----------------------
    # ZOOM: POWER
    # ----------------------
    ax = axes_zoom[0]

    ax.plot(time_zoom, df.loc[zoom_mask, cfg["col1"]],
            color="blue", alpha=0.3)

    ax.plot(time_zoom, df.loc[zoom_mask, cfg["col2"]],
            color="orange")

    ax.set_ylim(0, 80)
    ax.set_xlim(x0, x1)
    ax.grid(True, alpha=0.25)
    ax.set_xticks([])
    ax.set_yticks([])

    # Date label
    start_dt = pd.to_datetime(zoom_start)
    end_dt = pd.to_datetime(zoom_end)

    ax.text(
        0.5, 0.03,
        f"{start_dt:%b %d} – {end_dt:%b %d, %Y}",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        bbox=dict(facecolor="white", edgecolor="black", pad=2)
    )

    # ----------------------
    # ZOOM: CLEAN
    # ----------------------
    ax = axes_zoom[1]

    ax.imshow(np.expand_dims(clean_norm[zoom_mask], axis=0),
              aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[x0, x1, 0, 1])

    ax.set_xlim(x0, x1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    # ----------------------
    # ZOOM: PRICE
    # ----------------------
    ax = axes_zoom[2]

    ax.imshow(np.expand_dims(price_norm[zoom_mask], axis=0),
              aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[x0, x1, 0, 1])

    ax.set_xlim(x0, x1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    # ----------------------
    # AXES FORMAT
    for ax in axes_main:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


    for ax in axes_main:
        ax.tick_params(labelsize=PLOT_CONFIG["tick_label_size"])
        ax.margins(x=0)

    for ax in axes_main[:-1]:
        ax.tick_params(labelbottom=False)

    plt.subplots_adjust(
        left=0.03,
        right=0.98,
        bottom=0.10,
        top=0.95,
        hspace=0.05,   # ✅ tighter vertical spacing
        wspace=0.02
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


if __name__ == "__main__":
    run()