import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from pathlib import Path
import pandas as pd

# ==================================================
# PROJECT ROOT DETECTION
# ==================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

PROJECT_ROOT = get_project_root()

# ==================================================
# OUTPUT PATH
# ==================================================
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==================================================
# Stack and cell parameters
# ==================================================
N_cells = 65
A_active_cm2 = 214.0   # Active area per cell [cm^2]

# ==================================================
# Measured stack data
# ==================================================
P_V = np.array([
    0, 3.914, 5.616, 8.268, 11.01, 12.75, 15.232, 20.47,
    25.606, 30.734, 35.96, 40.95, 46.08, 51.22,
    52.39, 53.176, 54.349, 55.52, 56.304, 57.088
])

V_stack = np.array([
    100, 103, 104, 106, 109, 109, 112, 115, 118, 121,
    124, 126, 128, 131, 134, 136, 139, 142, 144, 146
])

P_I = np.array([
    0.0, 3.914, 5.616, 8.268, 11.01, 12.75, 15.232, 20.47,
    25.606, 30.734, 35.96, 40.95, 46.08, 51.22,
    52.39, 53.176, 54.349, 55.52, 56.304, 57.088
])

I_stack = np.array([
    0, 38, 54, 78, 101, 117, 138, 178, 217, 254,
    290, 325, 360, 391, 391, 391, 391, 391, 391, 391
])

# ==================================================
# Interpolation
# ==================================================
P_V_smooth = np.linspace(P_V.min(), P_V.max(), 300)
P_I_smooth = np.linspace(P_I.min(), P_I.max(), 300)

V_stack_fit = PchipInterpolator(P_V, V_stack)(P_V_smooth)
I_stack_fit = PchipInterpolator(P_I, I_stack)(P_I_smooth)

# ==================================================
# Plot styling
# ==================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 12,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "lines.linewidth": 2.5,
    "lines.markersize": 8,
})

# ==================================================
# FIGURE 1: Stack Voltage & Current vs Power
# ==================================================
plt.figure(figsize=(7, 4))
plt.grid(True, alpha=0.25)

plt.plot(P_V, V_stack, 'D', color='tab:blue', linestyle='None', label='Voltage')
plt.plot(P_I, I_stack, 'o', color='tab:orange', linestyle='None', label='Current')

plt.plot(P_V_smooth, V_stack_fit, color='tab:blue', linewidth=3, label='Voltage PCHIP fit')
plt.plot(P_I_smooth, I_stack_fit, color='tab:orange', linewidth=3, label='Current PCHIP fit')

plt.xlabel('Stack Power, $P_{\\mathrm{stack}}$ (kW)')
plt.ylabel('Stack Voltage (V) / Current (A)')
plt.xlim(0, 60)
plt.ylim(0, 400)

plt.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, 0.02),
    ncol=2,
    frameon=True,
    handlelength=2.0,
    handletextpad=0.6,
    labelspacing=0.2,
    columnspacing=0.8
)

filename = "stack_voltage_current_vs_power.pdf"
output_path = OUTPUT_DIR / filename
plt.tight_layout()
plt.savefig(output_path, format="pdf", bbox_inches="tight")
print(f"✅ Saved figure to: {output_path}")
plt.show()

# ==================================================
# FIGURE 2: Polarization curve
# ==================================================
V_cell = V_stack / N_cells
j_density = I_stack / A_active_cm2

j_max = j_density.max()
is_limited = np.isclose(j_density, j_max, atol=1e-6)

j_cc = j_density[~is_limited]
V_cc = V_cell[~is_limited]

j_lim = j_density[is_limited]
V_lim = V_cell[is_limited]

sort_idx = np.argsort(j_cc)
j_cc_sorted = j_cc[sort_idx]
V_cc_sorted = V_cc[sort_idx]

j_smooth = np.linspace(j_cc_sorted.min(), j_cc_sorted.max(), 300)
V_cell_fit = PchipInterpolator(j_cc_sorted, V_cc_sorted)(j_smooth)

j_end = j_smooth[-1]
V_end = V_cell_fit[-1]

plt.figure(figsize=(7, 4))
plt.grid(True, alpha=0.25)

plt.axvline(j_max, color='gray', linestyle='--', linewidth=2, label='SMPS current limit')

plt.plot(j_cc_sorted, V_cc_sorted, 'o', color='tab:blue', label='Current-controlled points')
plt.plot(j_smooth, V_cell_fit, color='tab:blue', linewidth=3, label='Polarization curve')

plt.plot([j_end, j_lim[0]], [V_end, V_lim[0]], color='tab:blue', linewidth=3)

plt.plot(j_lim, V_lim, '_', color='tab:red', markersize=12, label='Current-limited points')
plt.plot(j_lim, V_lim, color='tab:red', linewidth=3, label='Current-limited regime')

plt.xlabel('Current Density, $j$ (A cm$^{-2}$)')
plt.ylabel('Cell Voltage, $V_{\\mathrm{cell}}$ (V)')
plt.xlim(0, 2.00)
plt.ylim(1.2, 2.4)

plt.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, 0.02),
    ncol=2,
    frameon=True,
    handlelength=2.0,
    handletextpad=0.6,
    labelspacing=0.2,
    columnspacing=0.8
)

filename = "corrected_cell_polarization_with_limit.pdf"
output_path = OUTPUT_DIR / filename
plt.tight_layout()
plt.savefig(output_path, format="pdf", bbox_inches="tight")
print(f"✅ Saved figure to: {output_path}")
plt.show()



