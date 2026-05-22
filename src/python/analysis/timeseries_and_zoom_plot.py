import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ==================================================
# CONFIGURATION
# ==================================================
PLOT_CONFIG = {
    "title_size": 14,
    "axis_label_size": 14,
    "tick_label_size": 12,
    "legend_size": 11,
}

# ✅ DEFINE YOUR PLOTS HERE
PLOTS = [
    {
        "col1": "System Power (kW)",
        "col2": "System Power Avg (kW)",
        "label1": "15-minute",
        "label2": "14-day moving average",
        "ylabel": "System Power (kW)"
    },
]

# ✅ ZOOM WINDOW
ZOOM_RANGE = ("2025-04-16", "2025-04-20")

# ==================================================
# PROJECT ROOT
# ==================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# ==================================================
# FILE SELECTION
# ==================================================
def select_file():
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select data file",
        initialdir=PROJECT_ROOT / "outputs" / "tables",
        filetypes=[
            ("Data files", "*.csv *.xlsx *.xls"),
            ("All files", "*.*")
        ]
    )

    return Path(file_path) if file_path else None

# ==================================================
# LOAD DATA
# ==================================================
def load_data(file_path: Path):

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df.columns = df.columns.str.strip()

    if "time" not in df.columns:
        raise ValueError("Data must contain a 'time' column.")

    df["time"] = pd.to_datetime(df["time"])

    return df

# ==================================================
# FULL TIMELINE FIGURE
# ==================================================
def plot_full(df, cfg):

    col1 = cfg["col1"]
    col2 = cfg["col2"]
    label1 = cfg["label1"]
    label2 = cfg["label2"]
    ylabel = cfg.get("ylabel", "Value")

    zoom_start = pd.to_datetime(ZOOM_RANGE[0])
    zoom_end = pd.to_datetime(ZOOM_RANGE[1])

    fig, ax = plt.subplots(figsize=(12, 3))

    ax.plot(df["time"], df[col1],
            color="blue", alpha=0.2, linewidth=1.8)

    ax.plot(df["time"], df[col2],
            color="orange", alpha=1.0, linewidth=1.8)

    # Highlight zoom window
    #ax.axvspan(zoom_start, zoom_end,
    #           color="red", alpha=0.15,
    #           label="Zoom Window")

    ax.set_xlabel("Time", fontsize=PLOT_CONFIG["axis_label_size"])
    ax.set_ylabel(ylabel, fontsize=PLOT_CONFIG["axis_label_size"])

    ax.tick_params(labelsize=PLOT_CONFIG["tick_label_size"])
    ax.grid(True, alpha=0.3)

    ax.margins(x=0, y=0)

    ax.legend(
        [label1, label2, "Zoom Window"],
        fontsize=PLOT_CONFIG["legend_size"],
        loc="upper right"
    )

    plt.tight_layout()
    plt.show()

# ==================================================
# ZOOM FIGURE
# ==================================================
def plot_zoom(df, cfg):

    col1 = cfg["col1"]
    col2 = cfg["col2"]
    label1 = cfg["label1"]
    label2 = cfg["label2"]

    zoom_start = pd.to_datetime(ZOOM_RANGE[0])
    zoom_end = pd.to_datetime(ZOOM_RANGE[1])

    df_zoom = df[(df["time"] >= zoom_start) & (df["time"] <= zoom_end)]

    fig, ax = plt.subplots(figsize=(4, 4))

    line1, = ax.plot(df_zoom["time"], df_zoom[col1],
                     color="blue", alpha=0.2, linewidth=0.8)

    line2, = ax.plot(df_zoom["time"], df_zoom[col2],
                     color="orange", alpha=1.0, linewidth=1.5)

    # ✅ Remove Y axis
    ax.set_yticks([])
    ax.set_ylabel("")

    # ✅ DAY + YEAR labels
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    ax.tick_params(axis="x",
                   rotation=0,
                   labelsize=PLOT_CONFIG["tick_label_size"])

    ax.grid(True, alpha=0.3)

    # ✅ Legend
    ax.legend(
        [line1, line2],
        [label1, label2],
        fontsize=PLOT_CONFIG["legend_size"],
        loc="lower right"
    )

    ax.margins(x=0, y=0)

    # ✅ FULL BORDER (all sides visible)
    for spine in ax.spines.values():
        spine.set_visible(True)

    plt.tight_layout()
    plt.show()

# ==================================================
# MAIN PIPELINE
# ==================================================
def run_plot_template():

    file_path = select_file()
    if not file_path:
        print("No file selected.")
        return

    df = load_data(file_path)

    for cfg in PLOTS:
        plot_full(df, cfg)
        plot_zoom(df, cfg)

# ==================================================
# ENTRY
# ==================================================
if __name__ == "__main__":
    run_plot_template()
