import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
import os

# =========================================================
# Create output directory
# =========================================================
os.makedirs('figures', exist_ok=True)

# =========================================================
# Data
# =========================================================

# Output power (kW)
P_cal = np.array([5, 10, 20, 30, 40, 50, 60])

# Power factor
pf_cal = np.array([0.65, 0.71, 0.80, 0.86, 0.905, 0.92, 0.93])

# Efficiency (%)
eta_cal = np.array([80, 86, 91, 92, 92.5, 93, 93.5])

# Smooth axis
P_smooth = np.linspace(P_cal.min(), P_cal.max(), 300)

# Interpolation
pf_smooth = PchipInterpolator(P_cal, pf_cal)(P_smooth)
eta_smooth = PchipInterpolator(P_cal, eta_cal)(P_smooth)

# =========================================================
# Styling
# =========================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
})

# =========================================================
# Plot (Dual Axis)
# =========================================================
fig, ax1 = plt.subplots(figsize=(7, 4))

# -------------------------
# Left axis (Efficiency)
# -------------------------
ax1.plot(
    P_cal, eta_cal,
    'D',
    color='tab:blue',
    markerfacecolor='none',
    markeredgewidth=1.8,
    linestyle='None',
    label='Efficiency (data)'
)

ax1.plot(
    P_smooth, eta_smooth,
    color='tab:blue',
    linewidth=3,
    label='Efficiency (PCHIP)'
)

ax1.set_xlabel('Output Power, P$_{out}$ (kW)')
ax1.set_ylabel('AC/DC Conversion Efficiency (%)', color='black')
ax1.tick_params(axis='y', colors='black')
ax1.set_ylim(70, 100)

# -------------------------
# Right axis (Power Factor)
# -------------------------
ax2 = ax1.twinx()

ax2.plot(
    P_cal, pf_cal,
    's',
    color='tab:green',
    markerfacecolor='none',
    markeredgewidth=1.8,
    linestyle='None',
    label='Power Factor (data)'
)

ax2.plot(
    P_smooth, pf_smooth,
    color='tab:green',
    linewidth=3,
    label='Power Factor (PCHIP)'
)

ax2.set_ylabel('Power Factor', color='black')
ax2.tick_params(axis='y', colors='black')
ax2.set_ylim(0.6, 1.0)

# -------------------------
# Grid + limits
# -------------------------
ax1.set_xlim(0, 70)
ax1.grid(True, alpha=0.25)

# -------------------------
# Combined legend
# -------------------------
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()

ax1.legend(
    lines_1 + lines_2,
    labels_1 + labels_2,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.02),
    ncol=2,
    frameon=True
)

# -------------------------
# Save
# -------------------------
plt.tight_layout()
plt.savefig('figures/efficiency_and_pf_vs_power.pdf')

plt.show()
