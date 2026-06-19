import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# =========================================================
# PROJECT ROOT DETECTION
# =========================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# =========================================================
# PATHS
# =========================================================
DATA_DIR = PROJECT_ROOT / "data" / "experiment"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# STYLE (publication-ready)
# =========================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "lines.linewidth": 2.5,
})

# =========================================================
# SETTINGS
# =========================================================
skip_minutes = 10
step_seconds = 30 * 60

FIG_SIZE = (7, 4)  # optimized for LaTeX side-by-side

# =========================================================
# LOAD FUNCTION
# =========================================================
def load_var(filename, col):
    return pd.read_csv(DATA_DIR / filename, header=None, names=[col])

# =========================================================
# LOAD DATA
# =========================================================
timestamp = pd.read_csv(
    DATA_DIR / "timestamp.txt",
    header=None,
    names=["Time"],
    parse_dates=["Time"],
    date_format="%d-%b-%Y %H:%M:%S"
)

h2 = load_var("hydrogen_flow.txt", "H2")
cs_h2 = load_var("hydrogen_flow_cs.txt", "CS_H2")

pcmd  = load_var("power_command.txt", "Cmd")
stack = load_var("stack_power.txt", "Stack")
rect  = load_var("smps_power.txt", "SMPS")
chill = load_var("chiller_power.txt", "Chiller")
subs  = load_var("subsystem_power.txt", "Subsystem")

# =========================================================
# SANITY CHECK
# =========================================================
n = len(timestamp)
assert all(len(arr) == n for arr in [
    h2, cs_h2, pcmd, stack, rect, chill, subs
]), "Data length mismatch between files"

# =========================================================
# MERGE DATA
# =========================================================
df = timestamp.copy()

df["H2"] = h2["H2"]
df["CS_H2"] = cs_h2["CS_H2"]

df["Stack"] = stack["Stack"]
df["SMPS"] = rect["SMPS"]
df["Chiller"] = chill["Chiller"]
df["Subsystem"] = subs["Subsystem"]
df["Cmd"] = pcmd["Cmd"]

# Ensure correct ordering (safety)
df = df.sort_values("Time").reset_index(drop=True)

# =========================================================
# REMOVE INITIAL TRANSIENT
# =========================================================
start_time = df["Time"].iloc[0] + pd.Timedelta(minutes=skip_minutes)
df = df[df["Time"] >= start_time].reset_index(drop=True)

# =========================================================
# STEP AVERAGING
# =========================================================
dt = df["Time"].diff().dt.total_seconds().median()
samples_per_step = max(1, int(round(step_seconds / dt)))

step_means = []
step_intervals = []

for i in range(0, len(df), samples_per_step):
    seg = df.iloc[i:i + samples_per_step]
    if len(seg) == 0:
        continue
    step_means.append(seg["H2"].mean())
    step_intervals.append((seg["Time"].iloc[0], seg["Time"].iloc[-1]))

# =========================================================
# CONSISTENT X-TICKS
# =========================================================
base_day = df["Time"].iloc[0].normalize()
xticks = pd.date_range(
    start=base_day + pd.Timedelta(hours=14),
    end=base_day + pd.Timedelta(hours=17, minutes=30),
    freq="30min"
)

# =========================================================
# FIGURE 1 — SYSTEM POWER
# =========================================================
fig1, ax1 = plt.subplots(figsize=FIG_SIZE)

ax1.stackplot(
    df["Time"],
    df["Chiller"],
    df["Subsystem"],
    df["SMPS"],
    labels=["Chiller", "Subsystems", "SMPS (AC)"],
    alpha=0.7
)

ax1.plot(df["Time"], df["Stack"], label="Stack Power", color="#f1c40f")
ax1.plot(df["Time"], df["Cmd"], "--", label="Power Command", color="black")

ax1.set_ylabel("Power (kW)")
ax1.set_xlabel("Time")
ax1.set_ylim(bottom=0)

ax1.set_xticks(xticks)
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

ax1.grid(alpha=0.25)
ax1.legend(loc="upper right")

fig1.tight_layout()

fig1.savefig(
    OUTPUT_DIR / "system_power.pdf",
    bbox_inches="tight"
)


# =========================================================
# FIGURE 2 — HYDROGEN FLOW (WITH STEP LABELS)
# =========================================================
fig2, ax2 = plt.subplots(figsize=FIG_SIZE)

# Measured flow
ax2.fill_between(
    df["Time"],
    df["H2"],
    color="green",
    alpha=0.35,
    label="Measured Flow"
)

# Step averages + labels
for i, ((t0, t1), avg) in enumerate(zip(step_intervals, step_means)):

    ax2.hlines(
        avg,
        xmin=t0,
        xmax=t1,
        colors="red",
        linestyles="--",
        linewidth=2.0,
        label="Step-averaged flow" if i == 0 else "_nolegend_"
    )

    if i == len(step_means) - 1:
        continue

    midpoint = t0 + (t1 - t0) / 2

    ax2.annotate(
        f"{avg:.3f}",
        xy=(midpoint, avg),
        xytext=(0, 6),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=10,
        color="red",
        fontweight="bold",
        zorder=5
    )

# Manufacturer curve
ax2.plot(
    df["Time"],
    df["CS_H2"],
    color="black",
    linewidth=2.0,
    label="C-Series Reported Flow"
)

ax2.set_ylabel(r"H$_2$ Flow Rate (kg·h$^{-1}$)")
ax2.set_xlabel("Time")
ax2.set_ylim(0, 1.0)

ax2.set_xticks(xticks)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

ax2.grid(alpha=0.25)
ax2.legend(loc="upper right")

fig2.tight_layout()

fig2.savefig(
    OUTPUT_DIR / "hydrogen_flow.pdf",
    bbox_inches="tight"
)

plt.show()
