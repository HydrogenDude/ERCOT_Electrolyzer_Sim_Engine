import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

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
# OUTPUT PATH
# =========================================================
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_path = OUTPUT_DIR / "efficiency_curves.pdf"

# =========================================================
# CONSTANTS
# =========================================================
HHV_H2 = 39.4
LHV_H2 = 33.33

# =========================================================
# DATA
# =========================================================
stack_power_kW  = np.array([15.6, 20.8, 26, 31.2, 36.4, 41.6, 46.8, 52])
system_power_kW = np.array([36.4, 41.8, 47.3, 52.9, 58.4, 63.9, 69.4, 74.9])

gross_flow_kg_per_hr = np.array([0.32, 0.40, 0.49, 0.58, 0.66, 0.73, 0.82, 0.89])
net_flow_kg_per_hr   = np.array([0.20, 0.28, 0.37, 0.46, 0.54, 0.61, 0.70, 0.77])

# =========================================================
# ENERGY OUTPUT
# =========================================================
gross_HHV_kW = gross_flow_kg_per_hr * HHV_H2
gross_LHV_kW = gross_flow_kg_per_hr * LHV_H2
net_HHV_kW   = net_flow_kg_per_hr   * HHV_H2
net_LHV_kW   = net_flow_kg_per_hr   * LHV_H2

# =========================================================
# EFFICIENCY (convert to %)
# =========================================================
stack_g_hhv = (gross_HHV_kW / stack_power_kW) * 100
stack_n_hhv = (net_HHV_kW   / stack_power_kW) * 100
stack_g_lhv = (gross_LHV_kW / stack_power_kW) * 100
stack_n_lhv = (net_LHV_kW   / stack_power_kW) * 100

system_g_hhv = (gross_HHV_kW / system_power_kW) * 100
system_n_hhv = (net_HHV_kW   / system_power_kW) * 100
system_g_lhv = (gross_LHV_kW / system_power_kW) * 100
system_n_lhv = (net_LHV_kW   / system_power_kW) * 100

# =========================================================
# FIT FUNCTION
# =========================================================
def fit_line(x, y):
    coeffs = np.polyfit(x, y, 2)
    x_fit = np.linspace(min(x), max(x), 200)
    y_fit = np.polyval(coeffs, x_fit)
    return x_fit, y_fit

# Fits
x_s, sg_hhv = fit_line(stack_power_kW, stack_g_hhv)
_,  sn_hhv = fit_line(stack_power_kW, stack_n_hhv)
_,  sg_lhv = fit_line(stack_power_kW, stack_g_lhv)
_,  sn_lhv = fit_line(stack_power_kW, stack_n_lhv)

x_sys, syg_hhv = fit_line(system_power_kW, system_g_hhv)
_,     syn_hhv = fit_line(system_power_kW, system_n_hhv)
_,     syg_lhv = fit_line(system_power_kW, system_g_lhv)
_,     syn_lhv = fit_line(system_power_kW, system_n_lhv)

# =========================================================
# STYLE
# =========================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "lines.linewidth": 2.5,
    "lines.markersize": 7,
})

plt.figure(figsize=(7, 4))  # optimized for LaTeX

# ---------------- LHV (background) ---------------- #
plt.plot(x_s, sg_lhv, color="tab:orange", alpha=0.5, label=r"Stack$_{\mathrm{G,\,LHV}}$")
plt.plot(x_s, sn_lhv, color="tab:orange", alpha=0.5, linestyle="--", label=r"Stack$_{\mathrm{N,\,LHV}}$")

plt.plot(x_sys, syg_lhv, color="tab:red", alpha=0.5, label=r"System$_{\mathrm{G,\,LHV}}$")
plt.plot(x_sys, syn_lhv, color="tab:red", alpha=0.5, linestyle="--", label=r"System$_{\mathrm{N,\,LHV}}$")

# ---------------- HHV (foreground) ---------------- #
plt.scatter(stack_power_kW, stack_g_hhv, color="tab:blue")
plt.plot(x_s, sg_hhv, color="tab:blue", label=r"Stack$_{\mathrm{G,\,HHV}}$")

plt.scatter(stack_power_kW, stack_n_hhv, color="tab:blue")
plt.plot(x_s, sn_hhv, color="tab:blue", linestyle="--", label=r"Stack$_{\mathrm{N,\,HHV}}$")

plt.scatter(system_power_kW, system_g_hhv, color="tab:green")
plt.plot(x_sys, syg_hhv, color="tab:green", label=r"System$_{\mathrm{G,\,HHV}}$")

plt.scatter(system_power_kW, system_n_hhv, color="tab:green")
plt.plot(x_sys, syn_hhv, color="tab:green", linestyle="--", label=r"System$_{\mathrm{N,\,HHV}}$")


# ---------------- Formatting ---------------- #
plt.ylim(0, 100)
plt.ylabel("Efficiency (%)")
plt.xlabel("Electrical Power Input (kW)")
plt.grid(True, alpha=0.3)

plt.legend(
    loc="upper right",
    ncol=4,
    frameon=True,
    handlelength=1.6,
    columnspacing=0.8,   # ↓ horizontal spacing between columns
    labelspacing=0.05,    # ↓ vertical spacing between rows
    handletextpad=0.4,   # ↓ space between line and text
    borderpad=0.4       # ↓ padding inside legend box
)


plt.tight_layout()

# =========================================================
# SAVE
# =========================================================
plt.savefig(output_path, format="pdf", bbox_inches="tight")
print(f"✅ Saved figure to: {output_path}")

plt.show()