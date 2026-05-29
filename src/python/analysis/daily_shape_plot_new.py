import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, simpledialog

# --------------------------
# GLOBAL PLOT CONFIG
# --------------------------
PLOT_CONFIG = {
    "mode": "probability",

    "figsize": (7, 5),
    "background_color": "white",

    "ridge_gap_fraction": 0.08,
    "line_width": 1.2,
    "highlight_year": 2020,
    "highlight_line_width": 2.4,

    "fixed_y_max": 1.0,

    "colormap": plt.cm.winter,
    "color_min": 0.1,
    "color_max": 0.9,

    "alpha_min": 0.6,
    "alpha_max": 0.8,

    "xlim": (0, 95),
    "xticks": [48],
    "xtick_labels": ["12:00"],

    "grid": True,
    "grid_alpha": 0.2,
    "grid_style": "--",
    "vertical_line_x": 48,
    "vertical_line_alpha": 0.3,

    "ylabel": "Year",
    "xlabel": "Time of Day",

    "font": {
        "family": "sans-serif",
        "size": 14,
        "season_size": 14,
    #    "season_weight": "bold",
    },

    "hide_spines": ["top", "right"],
}

plt.rcParams.update({
    "font.family": PLOT_CONFIG["font"]["family"],
    "font.size": PLOT_CONFIG["font"]["size"],
})

seasons = ["Spring", "Summer", "Fall", "Winter"]
time_axis = np.arange(96)

# --------------------------
# STYLE
# --------------------------
def get_style(i, n):
    cfg = PLOT_CONFIG

    # Normalize index to [0,1]
    norm = i / (n - 1 if n > 1 else 1)

    # Proper colormap scaling
    cmap_val = cfg["color_min"] + (cfg["color_max"] - cfg["color_min"]) * norm
    color = cfg["colormap"](cmap_val)

    alpha = cfg["alpha_min"] + (cfg["alpha_max"] - cfg["alpha_min"]) * norm

    return color, alpha


def format_axis(ax, y_max):
    cfg = PLOT_CONFIG

    ax.set_xlim(*cfg["xlim"])
    ax.set_ylim(0, y_max)

    ax.set_xticks(cfg["xticks"])
    ax.set_xticklabels(cfg["xtick_labels"])

    if cfg["grid"]:
        ax.grid(True, axis='x', alpha=cfg["grid_alpha"], linestyle=cfg["grid_style"])

    if cfg["vertical_line_x"] is not None:
        ax.axvline(cfg["vertical_line_x"], linestyle=cfg["grid_style"],
                   alpha=cfg["vertical_line_alpha"])

    for s in cfg["hide_spines"]:
        ax.spines[s].set_visible(False)


# --------------------------
# LOAD DATA
# --------------------------
root = tk.Tk(); root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select data file",
    filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls")]
)

df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)

df.columns = df.columns.str.strip()
df['time'] = pd.to_datetime(df['time'], errors='coerce')
df = df.dropna(subset=['time'])

# --------------------------
# SELECT VARIABLE
# --------------------------
numeric_cols = [c for c in df.columns if c != 'time']

menu = "\n".join([f"{i}: {c}" for i, c in enumerate(numeric_cols)])
selection = simpledialog.askinteger("Column", menu)
var = numeric_cols[selection]

# --------------------------
# TIME FEATURES
# --------------------------
df = df.sort_values('time')
df['year'] = df['time'].dt.year
df['month'] = df['time'].dt.month
df['date'] = df['time'].dt.date
df['step'] = df.groupby('date').cumcount()

def get_season(m):
    return ["Winter","Winter","Spring","Spring","Spring","Summer",
            "Summer","Summer","Fall","Fall","Fall","Winter"][m-1]

df['season'] = df['month'].apply(get_season)

# --------------------------
# COMPUTE
# --------------------------
def compute(df_subset):
    results = {}
    for year, g in df_subset.groupby('year'):
        profiles = [
            d.sort_values('step')[var].values
            for _, d in g.groupby('date') if len(d) == 96
        ]
        if profiles:
            arr = np.array(profiles)
            results[year] = np.mean(arr > 0, axis=0)
    return results

# --------------------------
# PRECOMPUTE
# --------------------------
all_data = {}
all_years = set()
global_max = 0

for s in seasons:
    data = compute(df[df['season'] == s])
    all_data[s] = data
    all_years.update(data.keys())

    for v in data.values():
        global_max = max(global_max, np.max(v))

all_years = sorted(all_years)
year_to_idx = {y: i for i, y in enumerate(all_years)}

gap = PLOT_CONFIG["ridge_gap_fraction"]
spacing = global_max * (1 + gap)
y_max = (len(all_years) - 1) * spacing + global_max

# --------------------------
# CREATE FIGURE (HORIZONTAL)
# --------------------------
fig, axes = plt.subplots(
    1, 4,
    figsize=(PLOT_CONFIG["figsize"][0], PLOT_CONFIG["figsize"][1]),
    sharey=True
)

fig.patch.set_facecolor(PLOT_CONFIG["background_color"])

# --------------------------
# PLOT
# --------------------------
for ax, season in zip(axes, seasons):

    data = all_data[season]

    for year in sorted(all_years, reverse=True):

        if year not in data:
            continue

        i = year_to_idx[year]
        offset = i * spacing
        vals = data[year]

        color, alpha = get_style(year_to_idx[year], len(all_years))

        ax.fill_between(time_axis, offset, vals + offset,
                        color=color, alpha=alpha)

        lw = PLOT_CONFIG["highlight_line_width"] if year == PLOT_CONFIG["highlight_year"] else PLOT_CONFIG["line_width"]

        ax.plot(time_axis, vals + offset,
                color='white', linewidth=lw)

    format_axis(ax, y_max)

    y_pos = [year_to_idx[y] * spacing for y in all_years]
    ax.set_yticks(y_pos)

    if ax != axes[0]:
        ax.set_yticklabels([])
        ax.tick_params(axis='y', length=0)
        ax.spines["left"].set_visible(False)
    else:
        ax.set_yticklabels([])
        ax.tick_params(axis='y', length=0)
        ax.spines["left"].set_visible(False)

# --------------------------
# FORCE SHARED Y AXIS TICKS
# --------------------------
y_pos = [year_to_idx[y] * spacing for y in all_years]

axes[0].set_yticks(y_pos)
axes[0].set_yticklabels(all_years)

# 🔒 Strong enforcement
axes[0].yaxis.set_major_locator(plt.FixedLocator(y_pos))
axes[0].yaxis.set_major_formatter(plt.FixedFormatter(all_years))
axes[0].tick_params(axis='y', pad=8, colors='black')
axes[0].spines["left"].set_visible(True)

# --------------------------
# LABELS + SPACING
# --------------------------
axes[0].set_ylabel("Year")

fig.supxlabel("Time of Day", y=0.05)

plt.tight_layout()

fig.subplots_adjust(
    wspace=0.03,
    left=0.1,
    right=0.98,
    top=0.88
)

# ✅ NOW place titles (important!)
for ax, season in zip(axes, seasons):
    pos = ax.get_position()
    x = (pos.x0 + pos.x1) / 2

    fig.text(
        x, pos.y1 + 0.02,
        season,
        ha='center',
        va='bottom',
        fontsize=14,
        fontweight='bold'
)


plt.show()
