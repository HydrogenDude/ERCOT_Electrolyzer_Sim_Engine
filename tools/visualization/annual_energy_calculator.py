import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

def select_files():
    """Select multiple data files."""
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select data files",
        filetypes=[("Data files", "*.txt *.csv")]
    )
    return file_paths

def compute_annual_energy(file_path):
    df = pd.read_csv(file_path)

    # Convert and index timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)

    # Power column (assumes one column like 'Coal')
    power_col = df.columns[0]

    # Convert MW → MWh (15-min timestep)
    df['Energy_MWh'] = df[power_col] * 0.25

    # Aggregate yearly
    annual = df['Energy_MWh'].resample('Y').sum()

    # Convert to TWh
    annual_TWh = annual / 1e6

    # Clean year index
    annual_TWh.index = annual_TWh.index.year

    return annual_TWh

def main():
    file_paths = select_files()

    if not file_paths:
        print("No files selected.")
        return

    combined_df = pd.DataFrame()

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        name = os.path.splitext(filename)[0]

        annual_TWh = compute_annual_energy(file_path)

        # Add as column to combined table
        combined_df[name] = annual_TWh

    # Sort by year
    combined_df.sort_index(inplace=True)

    print("\n===== Annual Energy Table (TWh) =====\n")

    # Pretty print with formatting
    print(combined_df.to_string(float_format="{:.3f}".format))

if __name__ == "__main__":
    main()
