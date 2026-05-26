import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, simpledialog

# --------------------------
# GLOBAL PLOT CONFIG
# --------------------------
PLOT_CONFIG = {

    # ✅ MODE SWITCH
    # "probability" = fraction of time > 0
    # "magnitude"   = average value (normalized)
    "mode": "probability",  # <<< CHANGE THIS

    # ---- Figure ----
    "figsize": (7, 5),
    "sharey": True,
    "background_color": "white",

    # ---- Ridgeline geometry ----
    "ridge_overlap_factor": 0.4,
    "line_width": 1.2,
    "highlight_year": 2020,
    "highlight_line_width": 2.4,

    # ---- Scaling ----
    "fixed_y_max": 1.0,

    # ---- Colors ----
    "colormap": plt.cm.winter, #plt.cm.managua,
    "color_min": 0.1,
    "color_max": 0.9,

    # ---- Alpha ----
    "alpha_min": 0.6,
    "alpha_max": 0.8,

    # ---- Axes ----
    "xlim": (0, 95),
    "xticks": [48],
    "xtick_labels": ["12:00"],

    # ---- Grid ----
    "grid": True,
    "grid_alpha": 0.2,
    "grid_style": "--",
    "vertical_line_x": 48,
    "vertical_line_alpha": 0.3,

    # ---- Labels ----
    "ylabel": "Year",
    "xlabel": "Time of Day",

    # ---- Typography ----
    "font": {
        "family": "sans-serif",
        "size": 14,
        "xlabel_size": 14,
        "ylabel_size": 14,
        "xtick_size": 14,
        "ytick_size": 14,
        "season_size": 14,
        "season_weight": "bold",
    },

    # ---- Spine visibility ----
    "hide_spines": ["top", "right"],
}

# ✅ Apply global font settings
plt.rcParams.update({
    "font.family": PLOT_CONFIG["font"]["family"],
    "font.size": PLOT_CONFIG["font"]["size"],
    "axes.labelsize": PLOT_CONFIG["font"]["xlabel_size"],
    "xtick.labelsize": PLOT_CONFIG["font"]["xtick_size"],
    "ytick.labelsize": PLOT_CONFIG["font"]["ytick_size"],
})

seasons = ["Winter", "Spring", "Summer", "Fall"]
time_axis = np.arange(96)


# --------------------------
# STYLE HELPERS
# --------------------------
def get_style(i, n):
    cfg = PLOT_CONFIG
    norm = i / (n - 1 if n > 1 else 1)

    color = cfg["colormap"](
        cfg["color_min"] + (cfg["color_max"] - cfg["color_min"]) * norm
    )

    alpha = cfg["alpha_min"] + (cfg["alpha_max"] - cfg["alpha_min"]) * norm

    return color, alpha


def format_axis(ax, season, y_max):
    cfg = PLOT_CONFIG
    fnt = cfg["font"]

    ax.set_xlim(*cfg["xlim"])
    ax.set_ylim(0, y_max)

    ax.set_xticks(cfg["xticks"])
    ax.set_xticklabels(cfg["xtick_labels"], fontsize=fnt["xtick_size"])

    ax.text(
        0.02, 0.95, season,
        transform=ax.transAxes,
        fontsize=fnt["season_size"],
        fontweight=fnt["season_weight"],
        ha='left', va='top'
    )

    if cfg["grid"]:
        ax.grid(True, axis='x',
                alpha=cfg["grid_alpha"],
                linestyle=cfg["grid_style"])

    if cfg["vertical_line_x"] is not None:
        ax.axvline(
            cfg["vertical_line_x"],
            linestyle=cfg["grid_style"],
            alpha=cfg["vertical_line_alpha"]
        )

    for s in cfg["hide_spines"]:
        ax.spines[s].set_visible(False)

    ax.tick_params(axis='y', labelsize=fnt["ytick_size"], length=0)


# --------------------------
# LOAD FILE
# --------------------------
root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select data file",
    filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls")]
)

df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)

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

menu = "\n".join(
    [f"{i}: {c}{' <-- recommended' if 'Power' in c else ''}"
     for i, c in enumerate(numeric_cols)]
)

selection = simpledialog.askinteger("Column Selection", menu)

if selection is None or selection < 0 or selection >= len(numeric_cols):
    raise ValueError("Invalid selection")

var = numeric_cols[selection]
print(f"Selected column: {var}")

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
# CORE COMPUTATION FUNCTION
# --------------------------
def compute_by_year(df_subset, mode, debug=True):

    results = {}

    for year, df_year in df_subset.groupby('year'):

        profiles = []

        for _, g in df_year.groupby('date'):
            if len(g) == 96:
                profiles.append(g.sort_values('step')[var].values)

        if len(profiles) == 0:
            continue

        profiles = np.array(profiles)

        # --------------------------
        # MODE SWITCH
        # --------------------------
        if mode == "probability":

            result = np.mean(profiles > 0, axis=0)

        elif mode == "magnitude":

            result = np.mean(profiles, axis=0)

            # ✅ Safe ON-power diagnostic
            on_values = profiles[profiles > 0]

            if debug:
                if len(on_values) > 0:
                    print(f"{year} Mean power when ON: {np.mean(on_values):.2f}")
                else:
                    print(f"{year} Mean power when ON: No ON events")

        else:
            raise ValueError("Invalid mode")

        # ✅ Replace any NaNs (just in case)
        result = np.nan_to_num(result, nan=0.0)

        results[year] = result

    return results

# --------------------------
# PRECOMPUTE
# --------------------------
cfg = PLOT_CONFIG

all_data = {}
global_max = 0
max_ridges = 0

for s in seasons:
    data = compute_by_year(df[df['season'] == s], cfg["mode"])
    all_data[s] = data
    max_ridges = max(max_ridges, len(data))

    for p in data.values():
        if len(p):
            global_max = max(global_max, np.max(p))

# ✅ Normalize magnitude mode
if cfg["mode"] == "magnitude":
    if global_max > 0:
        for s in all_data:
            for y in all_data[s]:
                all_data[s][y] = all_data[s][y] / global_max
    global_max = 1.0

elif cfg["fixed_y_max"] is not None:
    global_max = cfg["fixed_y_max"]

spacing = cfg["ridge_overlap_factor"] * global_max
y_max = (max_ridges - 1) * spacing + global_max


# --------------------------
# CREATE FIGURE
# --------------------------
fig, axes = plt.subplots(1, 4, figsize=cfg["figsize"], sharey=True)
fig.patch.set_facecolor(cfg["background_color"])


# --------------------------
# PLOT
# --------------------------
for ax, season in zip(axes, seasons):

    yearly_data = all_data[season]

    if not yearly_data:
        ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=14)
        continue

    years_pos = sorted(yearly_data.keys())
    year_to_index = {y: i for i, y in enumerate(years_pos)}
    years_draw = sorted(years_pos, reverse=True)

    for year in years_draw:

        i = year_to_index[year]
        values = yearly_data[year]
        offset = i * spacing

        color, alpha = get_style(i, len(years_pos))

        ax.fill_between(time_axis, offset, values + offset,
                        color=color, alpha=alpha)

        lw = cfg["highlight_line_width"] if year == cfg["highlight_year"] else cfg["line_width"]

        ax.plot(time_axis, values + offset,
                color='white',
                linewidth=lw, alpha=0.95)

    format_axis(ax, season, y_max)


# --------------------------
# SHARED Y AXIS
# --------------------------
if max_ridges:
    sample = next((s for s in seasons if all_data[s]), None)
    if sample:
        years = sorted(all_data[sample].keys())
        y_pos = [i * spacing for i in range(len(years))]

        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels(years, fontsize=14)

axes[0].set_ylabel(cfg["ylabel"], fontsize=14)

fig.text(
    0.5, 0.01,
    cfg["xlabel"],
    ha='center',
    fontsize=14
)



plt.tight_layout()
fig.subplots_adjust(wspace=0.05)
plt.show()
