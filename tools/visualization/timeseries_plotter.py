import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# -------------------------------
# USER CONFIG (EDIT THIS)
# -------------------------------
PLOT_CONFIG = {
    "title_size": 16,
    "axis_label_size": 14,
    "tick_label_size": 12,
    "legend_size": 11,
}

# -------------------------------
# Project root detection
# -------------------------------
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# -------------------------------
# File selection
# -------------------------------
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

# -------------------------------
# Load data
# -------------------------------
def load_data(file_path: Path):
    ext = file_path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df.columns = df.columns.str.strip()
    df['time'] = pd.to_datetime(df['time'])

    return df

# -------------------------------
# Column selection (PRIMARY)
# -------------------------------
def choose_primary_columns(df):
    print("\nAvailable columns:\n")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")

    selected = input("\nSelect PRIMARY axis columns (ordered indices):\n>> ")
    indices = [int(i.strip()) for i in selected.split(',')]

    return [df.columns[i] for i in indices]

# -------------------------------
# Column selection (SECONDARY)
# -------------------------------
def choose_secondary_columns(df):
    print("\nSelect SECONDARY axis columns (ordered indices):")
    selected = input(">> ")

    indices = [int(i.strip()) for i in selected.split(',')]
    return [df.columns[i] for i in indices]

# -------------------------------
# Alpha input (NEW)
# -------------------------------
def get_alpha_values(columns, label):
    print(f"\nEnter alpha values for {label} axis variables (0 to 1):")

    alphas = []
    for col in columns:
        val = input(f"  {col}: ")
        try:
            alpha = float(val)
            alpha = max(0.0, min(1.0, alpha))  # clamp to [0,1]
        except:
            alpha = 1.0
        alphas.append(alpha)

    return alphas

# -------------------------------
# Time filtering
# -------------------------------
def select_time_range(df):
    print("\nSelect time range:")
    print("1: Full dataset (default)")
    print("2: Default window (April 16–20, 2025)")
    print("3: Custom range")

    choice = input(">> ").strip()

    if choice == "2":
        start = pd.to_datetime("2025-04-16")
        end = pd.to_datetime("2025-04-20")

    elif choice == "3":
        start = pd.to_datetime(input("Start date (YYYY-MM-DD): "))
        end = pd.to_datetime(input("End date (YYYY-MM-DD): "))

    else:
        return df

    print(f"Using time range: {start} → {end}")
    return df[(df['time'] >= start) & (df['time'] <= end)]

# -------------------------------
# Plotting
# -------------------------------
def plot_data(df, primary_cols, primary_alphas, secondary_cols, secondary_alphas):

    df = select_time_range(df)

    fig, ax1 = plt.subplots(figsize=(7, 5))
    colors = plt.cm.tab10.colors

    # -------------------------------
    # PRIMARY AXIS
    # -------------------------------
    for i, col in enumerate(primary_cols):
        ax1.plot(
            df['time'],
            df[col],
            label=col.replace("_", " ").title(),
            color=colors[i % len(colors)],
            linewidth=1.8,
            alpha=primary_alphas[i],
            rasterized=True
        )

    ax1.set_xlabel("Time", fontsize=PLOT_CONFIG["axis_label_size"])
    ax1.set_ylabel("Primary Axis", fontsize=PLOT_CONFIG["axis_label_size"])
    ax1.tick_params(axis='both', labelsize=PLOT_CONFIG["tick_label_size"])
    ax1.grid(True, linestyle="--", alpha=0.25)

    # -------------------------------
    # SECONDARY AXIS
    # -------------------------------
    if secondary_cols:
        ax2 = ax1.twinx()

        for i, col in enumerate(secondary_cols):
            ax2.plot(
                df['time'],
                df[col],
                label=col.replace("_", " ").title(),
                linestyle="-",
                linewidth=0.8,
                alpha=secondary_alphas[i],
                rasterized=True
            )

        ax2.set_ylabel("Secondary Axis", fontsize=PLOT_CONFIG["axis_label_size"])
        ax2.tick_params(axis='y', labelsize=PLOT_CONFIG["tick_label_size"])

        # Merge legends
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()

        ax1.legend(
            lines_1 + lines_2,
            labels_1 + labels_2,
            fontsize=PLOT_CONFIG["legend_size"]
        )

    else:
        ax1.legend(fontsize=PLOT_CONFIG["legend_size"])

    ax1.margins(x=0)
    
    if secondary_cols:
        ax2.margins(x=0)

    plt.tight_layout()
    plt.show()

# -------------------------------
# Main
# -------------------------------
def main():
    file_path = select_file()

    if not file_path:
        print("No file selected.")
        return

    df = load_data(file_path)

    # PRIMARY
    primary_cols = choose_primary_columns(df)
    primary_alphas = get_alpha_values(primary_cols, "PRIMARY")

    # SECONDARY?
    print("\nDo you want a secondary axis? (y/n)")
    use_secondary = input(">> ").lower() == 'y'

    secondary_cols = []
    secondary_alphas = []

    if use_secondary:
        secondary_cols = choose_secondary_columns(df)
        secondary_alphas = get_alpha_values(secondary_cols, "SECONDARY")

    # Plot
    plot_data(df, primary_cols, primary_alphas, secondary_cols, secondary_alphas)

if __name__ == "__main__":
    main()