import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog
from scipy.spatial import ConvexHull

# =====================================================
# VISUAL STYLE CONTROL (EDIT THIS ONLY)
# =====================================================
STYLE = {
    # Font sizes
    "label_fs": 14,
    "tick_fs": 12,
    "legend_fs": 11,

    # Marker sizes
    "id1_size": 90,
    "scatter_size": 2,

    # Line widths
    "id1_edge_width": 1.2,
    "spine_width": 1.0,

    # Transparency
    "scatter_alpha": 0.5,

    # Tick appearance
    "tick_length": 3,

    # Figure
    "figsize": (7, 4),
    "dpi": 300,
}

# Apply global styling
plt.rcParams.update({
    "font.size": STYLE["label_fs"],
    "axes.labelsize": STYLE["label_fs"],
    "xtick.labelsize": STYLE["tick_fs"],
    "ytick.labelsize": STYLE["tick_fs"],
    "legend.fontsize": STYLE["legend_fs"],
    "axes.linewidth": STYLE["spine_width"],
})

# =====================================================
# USER CONFIGURATION
# =====================================================
P_LOW  = 0
P_HIGH = 88.2

REGION_MODE = False
REGION_PCT = (0, 88.2)
REGION_ALPHA = 0.1

PLOT_CONFIGS = [
    {"x": "h2",   "y": "co2"},
    {"x": "cost", "y": "h2"},
    {"x": "cost", "y": "co2"},
]

AXIS_LABELS = {
    "h2": "Total H$_2$ produced (kg)",
    "co2": "Total CO$_2$ emitted (kg)",
    "cost": "Electricity cost (USD)",
    "startups": "Electrolyzer startups",
}

GROUP_FILTER = {
    "DonOff": {"off"},
    "year": {2020, 2021, 2022, 2023, 2024, 2025},
    "S": {20, 69, 26},
}

ID1_MARKERS = ["X", "D", "P", "^", "v", "s", "*", "<", ">", "h"]

# =====================================================
# PROJECT ROOT
# =====================================================
def find_project_root(start_path: Path):
    for parent in [start_path.resolve()] + list(start_path.resolve().parents):
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Could not find .project-root")

PROJECT_ROOT = find_project_root(Path(__file__))
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# FILE SELECTION
# =====================================================
def select_h5_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    files = filedialog.askopenfilenames(
        title="Select HDF5 files",
        filetypes=[("HDF5 files", "*.h5")]
    )
    root.destroy()
    return [Path(f) for f in files]

h5_files = select_h5_files()
if not h5_files:
    raise RuntimeError("No files selected.")

# =====================================================
# PARSING
# =====================================================
pattern = re.compile(
    r"N(?P<N>\d+)_S(?P<S>\d+)_D(?P<D>on|off)_(?P<year>\d{4})",
    re.IGNORECASE,
)

def dataset_selected(data, filt):
    for k, allowed in filt.items():
        if data.get(k) not in allowed:
            return False
    return True

# =====================================================
# LOAD DATA
# =====================================================
used_axes = {cfg["x"] for cfg in PLOT_CONFIGS} | {cfg["y"] for cfg in PLOT_CONFIGS}

datasets = []
all_vals = {k: [] for k in used_axes}
all_startups = []

for fpath in h5_files:
    meta = {"DonOff": None, "year": None, "S": None}
    m = pattern.search(fpath.stem)
    if m:
        gd = m.groupdict()
        meta.update(
            DonOff=gd["D"].lower(),
            year=int(gd["year"]),
            S=int(gd["S"]),
        )

    if not dataset_selected(meta, GROUP_FILTER):
        continue

    with h5py.File(fpath, "r") as f:
        data = dict(meta)
        data["label"] = fpath.stem
        data["h2"] = f["/totals/total_h2_kg"][:].ravel()
        data["co2"] = f["/totals/total_co2_kg"][:].ravel()
        data["cost"] = f["/totals/total_cost"][:].ravel()
        data["startups"] = f["/state/startups"][:].ravel()

    datasets.append(data)
    for k in used_axes:
        all_vals[k].append(data[k])
    all_startups.append(data["startups"])

if not datasets:
    raise RuntimeError("No datasets passed filters.")

# =====================================================
# COLORS
# =====================================================
norm = Normalize(
    vmin=np.percentile(np.concatenate(all_startups), 0),
    vmax=np.percentile(np.concatenate(all_startups), 99),
)
cmap = cm.jet

dataset_colors = {
    i: plt.get_cmap("tab10")(i % 10)
    for i in range(len(datasets))
}

axis_limits = {
    k: np.percentile(np.concatenate(v), [P_LOW, P_HIGH])
    for k, v in all_vals.items()
}

# =====================================================
# PLOT FUNCTION
# =====================================================
def plot_2d(ax, x_key, y_key):
    x_lo, x_hi = axis_limits[x_key]
    y_lo, y_hi = axis_limits[y_key]

    for i, data in enumerate(datasets):
        x, y, startups = data[x_key], data[y_key], data["startups"]
        marker = ID1_MARKERS[i % len(ID1_MARKERS)]

        # ID1 point
        ax.scatter(
            x[0], y[0],
            c=[startups[0]],
            cmap=cmap,
            norm=norm,
            marker=marker,
            s=STYLE["id1_size"],
            edgecolors="black",
            linewidths=STYLE["id1_edge_width"],
            zorder=100,
        )

        # Cloud
        inlier = (
            (x >= x_lo) & (x <= x_hi) &
            (y >= y_lo) & (y <= y_hi)
        )

        ax.scatter(
            x[inlier],
            y[inlier],
            c=startups[inlier],
            cmap=cmap,
            norm=norm,
            s=STYLE["scatter_size"],
            alpha=STYLE["scatter_alpha"],
            linewidth=0,
        )

    ax.set_xlabel(AXIS_LABELS[x_key])
    ax.set_ylabel(AXIS_LABELS[y_key])
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)

    ax.tick_params(
        length=STYLE["tick_length"],
        width=STYLE["spine_width"],
    )

    ax.grid(False)

# =====================================================
# GENERATE + SAVE FIGURES
# =====================================================
for idx, cfg in enumerate(PLOT_CONFIGS):

    fig, ax = plt.subplots(
        figsize=STYLE["figsize"],
        dpi=STYLE["dpi"]
    )

    plot_2d(ax, cfg["x"], cfg["y"])

    # Remove redundant x labels for stacking
    if idx < len(PLOT_CONFIGS) - 1:
        ax.set_xlabel("")

    plt.tight_layout(pad=0.5)

    fname = f"{cfg['x']}_vs_{cfg['y']}.pdf"
    save_path = OUTPUT_DIR / fname

    fig.savefig(save_path)
    plt.close(fig)

    print(f"Saved: {save_path}")