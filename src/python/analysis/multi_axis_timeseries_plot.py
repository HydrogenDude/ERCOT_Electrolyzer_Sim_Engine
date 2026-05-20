import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==================================================
# FIND PROJECT ROOT
# ==================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# ==================================================
# LOAD DATA
# ==================================================
csv_path = PROJECT_ROOT / "outputs" / "tables" / "default_case_timeseries.csv"
df = pd.read_csv(csv_path)

# Choose x-axis
x = df.index   # replace with df["time"] if needed


# ==================================================
# SCALING FUNCTION (CORE LOGIC)
# ==================================================
def apply_scale(series, scale):
    if scale is None or scale == "linear":
        return series

    # ✅ log → normalize (KEY FEATURE)
    if scale == "log+normalize":
        s = np.log10(series + 1e-9)
        smin, smax = s.min(), s.max()
        if smax - smin == 0:
            return np.zeros_like(s)
        return (s - smin) / (smax - smin)

    # ✅ normalize only
    if scale == "normalize":
        smin, smax = series.min(), series.max()
        if smax - smin == 0:
            return np.zeros_like(series)
        return (series - smin) / (smax - smin)

    # ✅ z-score
    if scale == "zscore":
        std = series.std()
        if std == 0:
            return np.zeros_like(series)
        return (series - series.mean()) / std

    # ✅ log only
    if scale == "log":
        return np.log10(series + 1e-9)

    # ✅ custom scaling
    if callable(scale):
        return scale(series)

    raise ValueError(f"Unknown scale type: {scale}")


# ==================================================
# MAIN SHAPE-COMPARISON PLOT FUNCTION
# ==================================================
def plot_timeseries(
    columns,
    scales=None,
    title=None
):
    """
    columns: list of column names
    scales: dict mapping column -> scale
            ("normalize", "log", "log+normalize", etc.)
    """

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = plt.cm.tab10.colors

    for i, col in enumerate(columns):

        if col not in df.columns:
            print(f"WARNING: '{col}' not found in dataset")
            continue

        scale = None
        if scales and col in scales:
            scale = scales[col]

        y = apply_scale(df[col], scale)

        ax.plot(
            x,
            y,
            color=colors[i % len(colors)],
            linewidth=1.6,
            alpha=0.9,
            label=f"{col} ({scale or 'linear'})"
        )

    # ✅ Force consistent bounds when normalizing
    if scales and any("normalize" in str(s) for s in scales.values()):
        ax.set_ylim(0, 1)

    ax.set_xlabel("Time / Index")
    ax.set_ylabel("Scaled Value")

    if title:
        ax.set_title(title)

    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    plt.tight_layout()
    plt.show()


# ==================================================
# OPTIONAL: MULTI-AXIS VERSION (for magnitude comparison)
# ==================================================
def plot_multi_axis(
    primary,
    secondary=None,
    primary_scale=None,
    secondary_scale=None
):

    fig, ax1 = plt.subplots(figsize=(12, 4))
    colors = plt.cm.tab10.colors

    # PRIMARY
    for i, col in enumerate(primary):
        y = apply_scale(df[col], primary_scale)

        ax1.plot(
            x, y,
            color=colors[i],
            label=col
        )

    ax1.set_ylabel(f"Primary ({primary_scale or 'linear'})")

    # SECONDARY
    if secondary:
        ax2 = ax1.twinx()

        for i, col in enumerate(secondary):
            y = apply_scale(df[col], secondary_scale)

            ax2.plot(
                x, y,
                linestyle='--',
                color=colors[i + len(primary)],
                label=col
            )

        ax2.set_ylabel(f"Secondary ({secondary_scale or 'linear'})")

    # COMBINED LEGEND
    lines, labels = ax1.get_legend_handles_labels()
    if secondary:
        l2, lab2 = ax2.get_legend_handles_labels()
        lines += l2
        labels += lab2

    ax1.legend(lines, labels)

    ax1.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.show()


# ==================================================
# ✅ EXAMPLE USAGE (YOUR CASE)
# ==================================================
if __name__ == "__main__":

    plot_timeseries(
        columns=[
            "energy_price",
            "co2_per_h2"
        ],

        scales={
            # ✅ LOG-FIRST then normalized (critical for price)
            "energy_price": "log+normalize",
            "co2_per_h2": "normalize"
        },

        title="Shape Comparison (Log-Scaled Energy Price)"
    )
