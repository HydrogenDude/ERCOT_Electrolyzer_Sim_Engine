import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
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
# ZOOM WINDOW (MANUAL CONTROL)
# ==================================================

zoom_start = "2025-04-16"
zoom_end   = "2025-04-21"

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
    norm[vals > clean_turndown] = 0.5 + (vals[vals > clean_turndown] - clean_turndown) / (1 - clean_turndown) * 0.5

    return np.clip(norm, 0, 1)


def normalize_price(vals):
    norm = np.zeros_like(vals, dtype=float)

    norm[vals >= price_stop] = 0.0
    mask = (vals >= price_turndown) & (vals < price_stop)
    norm[mask] = 0.5 - (vals[mask] - price_turndown) / (price_stop - price_turndown) * 0.5
    norm[vals < price_turndown] = 0.5 + (price_turndown - vals[vals < price_turndown]) / price_turndown * 0.5

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

    fig = plt.figure(figsize=(12, 5))

    gs = gridspec.GridSpec(
        3, 2,
        width_ratios=[12, 3],
        height_ratios=[3, 0.6, 0.6]
    )

    axes_main = [fig.add_subplot(gs[i, 0]) for i in range(3)]
    axes_zoom = [fig.add_subplot(gs[i, 1], sharey=axes_main[i]) for i in range(3)]

    fig.subplots_adjust(hspace=0.05, wspace=0.05)

    # ==================================================
    # ZOOM MASK
    # ==================================================

    zoom_mask = (time >= zoom_start) & (time <= zoom_end)

    time_zoom = time[zoom_mask]
    t_zoom_vals = mdates.date2num(time_zoom)

    # ==================================================
    # MAIN PLOTS (UNCHANGED STYLE)
    # ==================================================

    # --- POWER ---
    ax = axes_main[0]
    line1, = ax.plot(time, df[cfg["col1"]],
                     color="blue", alpha=0.3, linewidth=0.1)
    line2, = ax.plot(time, df[cfg["col2"]],
                     color="orange", linewidth=1.5)
    
    # --- SHADED REGION UNDER 14-DAY AVG ---
    ax.fill_between(
        time,
        df[cfg["col2"]],
        0,                      # baseline (y=0)
        color="orange",
        alpha=0.5,
        linewidth=0
    )


    ax.set_ylabel(cfg["ylabel"], fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_ylim(0, 80)
    ax.grid(True, alpha=0.25)

    legend = ax.legend(
        [line1, line2],
        [cfg["label1"], cfg["label2"]],
        fontsize=PLOT_CONFIG["legend_size"],
        loc="upper right"
    )
    for legline in legend.legend_handles:
        legline.set_linewidth(1.5)

    # --- CR ---
    ax = axes_main[1]
    img = np.expand_dims(clean_norm, axis=0)
    ax.imshow(img, aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])
    ax.set_ylabel("CR", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])
    ax.set_ylim(0, 1)

    # --- PRICE ---
    ax = axes_main[2]
    img = np.expand_dims(price_norm, axis=0)
    ax.imshow(img, aspect='auto', cmap=cmap, vmin=0, vmax=1,
              extent=[t_vals[0], t_vals[-1], 0, 1])
    ax.set_ylabel("$/MWh", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_yticks([])
    ax.set_ylim(0, 1)

    # ==================================================
    # ZOOM PLOTS (MATCH STYLE EXACTLY)
    # ==================================================

    # Precompute limits once
    x0, x1 = t_zoom_vals[0], t_zoom_vals[-1]

    # --- POWER ZOOM ---
    ax = axes_zoom[0]
    ax.plot(time_zoom, df.loc[zoom_mask, cfg["col1"]],
            color="blue", alpha=0.3, linewidth=1.5)

    ax.plot(time_zoom, df.loc[zoom_mask, cfg["col2"]],
            color="orange", linewidth=1.5)

    ax.set_ylim(0, 80)
    ax.set_xlim(x0, x1)            # ✅ FIX
    ax.margins(x=0)

    ax.grid(True, alpha=0.25)
    ax.set_xticks([])
    ax.set_yticks([])

    # ✅ Format date range string
    start_dt = pd.to_datetime(zoom_start)
    end_dt   = pd.to_datetime(zoom_end)

    date_text = f"{start_dt.strftime('%b %d')} – {end_dt.strftime('%b %d, %Y')}"

    # ✅ Add annotation (bottom-center inside axes)
    ax.text(
        0.5, 0.03,
        date_text,
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=10,
        color="black",
        bbox=dict(
            facecolor="white",
            alpha=1,
            edgecolor="black",
            pad=2
        )
    )

    # --- CR ZOOM ---
    ax = axes_zoom[1]
    img = np.expand_dims(clean_norm[zoom_mask], axis=0)

    ax.imshow(
        img,
        aspect='auto',
        cmap=cmap,
        vmin=0,
        vmax=1,
        extent=[x0, x1, 0, 1]
    )

    ax.set_ylim(0, 1)
    ax.set_xlim(x0, x1)            # ✅ FIX
    ax.margins(x=0)

    ax.set_xticks([])
    ax.set_yticks([])

    # --- PRICE ZOOM ---
    ax = axes_zoom[2]
    img = np.expand_dims(price_norm[zoom_mask], axis=0)

    ax.imshow(
        img,
        aspect='auto',
        cmap=cmap,
        vmin=0,
        vmax=1,
        extent=[x0, x1, 0, 1]
    )

    ax.set_ylim(0, 1)
    ax.set_xlim(x0, x1)            # ✅ FIX
    ax.margins(x=0)

    ax.set_xticks([])
    ax.set_yticks([])

    # ==================================================
    # AXIS FORMATTING
    # ==================================================

    axes_main[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes_main[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    for ax in axes_main:
        ax.tick_params(labelsize=PLOT_CONFIG["tick_label_size"])
        ax.margins(x=0, y=0)

    for ax in axes_main[:-1]:
        ax.tick_params(labelbottom=False)

    for ax in axes_main[:2]:
        ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

    fig.subplots_adjust(
        left=0.06,
        right=0.995,
        top=0.98,
        bottom=0.08,
        hspace=0.02,
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

# ==================================================
# ENTRY
# ==================================================

if __name__ == "__main__":
    run()