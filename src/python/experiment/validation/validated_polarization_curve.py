import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from pathlib import Path

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
# PARAMETERS
# ==================================================
N_cells = 65
A_active_cm2 = 214.0

# ==================================================
# MEASURED DATA
# ==================================================
I_stack = np.array([
    0, 38, 54, 78, 101, 117, 138, 178, 217, 254,
    290, 325, 360, 391, 391, 391, 391, 391, 391, 391
])

V_stack = np.array([
    100, 103, 104, 106, 109, 109, 112, 115, 118, 121,
    124, 126, 128, 131, 134, 136, 139, 142, 144, 146
])

# ==================================================
# CONVERT TO CELL POLARIZATION
# ==================================================
V_cell = V_stack / N_cells
j_density = I_stack / A_active_cm2

j_max = j_density.max()
is_limited = np.isclose(j_density, j_max, atol=1e-6)

j_cc = j_density[~is_limited]
V_cc = V_cell[~is_limited]

j_lim = j_density[is_limited]
V_lim = V_cell[is_limited]

# Sort for interpolation
sort_idx = np.argsort(j_cc)
j_cc = j_cc[sort_idx]
V_cc = V_cc[sort_idx]

# Main curve (PCHIP)
j_smooth = np.linspace(j_cc.min(), j_cc.max(), 300)
V_fit = PchipInterpolator(j_cc, V_cc)(j_smooth)

# ==================================================
# REFERENCE CURVE UTILITIES
# ==================================================
def fit_reference_curve(j, V, ref):
    # Sort input
    sort_idx = np.argsort(j)
    j_sorted = j[sort_idx]
    V_sorted = V[sort_idx]

    fit_type = ref.get("fit_type", "pchip")
    n_points = ref.get("num_points", 300)

    j_fit = np.linspace(j_sorted.min(), j_sorted.max(), n_points)

    if fit_type == "pchip":
        V_fit = PchipInterpolator(j_sorted, V_sorted)(j_fit)

    elif fit_type == "poly":
        degree = ref.get("degree", 3)
        coeffs = np.polyfit(j_sorted, V_sorted, degree)
        poly = np.poly1d(coeffs)
        V_fit = poly(j_fit)

    else:
        raise ValueError(f"Unknown fit_type: {fit_type}")

    return j_fit, V_fit


def plot_reference_curves(ax, reference_curves):
    for ref in reference_curves:
        j_fit, V_fit = fit_reference_curve(ref["j"], ref["V"], ref)

        ax.plot(
            j_fit,
            V_fit,
            color=ref.get("color", "black"),
            linestyle=ref.get("linestyle", "--"),
            linewidth=ref.get("linewidth", 2.0),
            label=ref.get("label", "Reference"),
            zorder=1,
            alpha=0.6
        )

# ==================================================
# DEFINE REFERENCE DATASETS
# ==================================================
reference_curves = [
    {
        "j": np.array([0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 1.9]),
        "V": np.array([1.6, 1.62, 1.68, 1.74, 1.79, 1.85, 1.9, 1.94, 1.99, 2.03, 2.05]),
        "label": "Stansberry (2020)",
        "color": "#62A350",
        "linestyle": "-",
        "linewidth": 2,
        "fit_type": "poly",
        "degree": 2
    },
    {
        "j": np.array([0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 1.93]),
        "V": np.array([1.59, 1.63, 1.7, 1.75, 1.81, 1.86, 1.91, 1.94, 2, 2.06, 2.09]),
        "label": "Crespi et al. (2023)",
        "color": "#A35091",
        "linestyle": "-",
        "linewidth": 2,
        "fit_type": "poly",
        "degree": 2
    },
]

# ==================================================
# STYLING
# ==================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 12,
    "lines.linewidth": 2.5,
    "lines.markersize": 6
})

# ==================================================
# PLOT
# ==================================================
plt.figure(figsize=(7, 4))
ax = plt.gca()

plt.grid(True, alpha=0.25)

# SMPS limit
plt.axvline(j_max, color='gray', linestyle='--', linewidth=2,
            label='SMPS current limit')

# Raw points (hidden from legend)
plt.plot(j_cc, V_cc, 'o', color='tab:blue')

# Main curve
plt.plot(j_smooth, V_fit, color='tab:blue', linewidth=3,
         label='Polarization curve')

# Transition
plt.plot([j_smooth[-1], j_lim[0]], [V_fit[-1], V_lim[0]],
         color='tab:blue', linewidth=3)

# Current-limited regime
plt.plot(j_lim, V_lim, '_', color='tab:red', markersize=12)
plt.plot(j_lim, V_lim, color='tab:red', linewidth=3,
         label='Current-limited regime')

# Reference curves
plot_reference_curves(ax, reference_curves)

# Labels
plt.xlabel('Current Density, $j$ (A cm$^{-2}$)')
plt.ylabel('Cell Voltage, $V_{\\mathrm{cell}}$ (V)')

plt.xlim(0, 2.0)
plt.ylim(1.2, 2.4)

# Legend (clean)
handles, labels = ax.get_legend_handles_labels()

seen = set()
filtered = [(h, l) for h, l in zip(handles, labels)
            if not (l in seen or seen.add(l))]

handles, labels = zip(*filtered)

plt.legend(
    handles, labels,
    loc="best",
    ncol=2,
    frameon=True,
    handlelength=2.0,
    handletextpad=0.6,
    labelspacing=0.2,
    columnspacing=0.8
)

# Save
filename = "polarization_with_references.pdf"
output_path = OUTPUT_DIR / filename

plt.tight_layout()
plt.savefig(output_path, format="pdf", bbox_inches="tight")
print(f"✅ Saved figure to: {output_path}")

plt.show()
