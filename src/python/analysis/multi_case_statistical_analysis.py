"""
Statistical analysis of the 2025 supervisory-control ensemble.

Companion to the cost-carbon scatter (Fig. 10). Rather than re-plotting the
ensemble, this quantifies the structure the figure shows: how tightly the
configurations collapse onto a single cost-carbon line, and how production
varies along that line. Reads the same HDF5 totals.

Dependencies: numpy, scipy, matplotlib, h5py
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# ==================================================
# SETTINGS
# ==================================================

H5_PATH = r"C:/Users/evan123/Desktop/large_sim_results/N10000_S69_Doff_2025.h5"
DEFAULT_IDX = 0          # default case is the first stored configuration
SMR_LOW, SMR_HIGH = 11.0, 14.0   # grey-SMR carbon intensity band (kg CO2 / kg H2)
N_BINS = 12              # cost bins for envelope-width profile
SAVE_FIG = "ensemble_envelope_stats_2025.png"

plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "figure.dpi": 120,
})

# ==================================================
# LOAD DATA
# ==================================================

print(f"\nLoading: {H5_PATH}")

with h5py.File(H5_PATH, "r") as f:
    total_cost = f["totals/total_cost"][:].ravel()
    total_co2  = f["totals/total_co2_kg"][:].ravel()
    total_h2   = f["totals/total_h2_kg"][:].ravel()

    # Startup count is optional; probe a few likely keys so the script still
    # runs if the field is named differently or absent.
    total_starts = None
    for key in ("totals/total_startups", "totals/total_starts",
                "totals/startups", "totals/n_startups"):
        if key in f:
            total_starts = f[key][:].ravel()
            break

# ==================================================
# DERIVE PER-KG METRICS
# ==================================================

valid = total_h2 > 1e-6

cost = total_cost[valid] / total_h2[valid]   # USD / kg H2
co2  = total_co2[valid]  / total_h2[valid]   # kg CO2 / kg H2
h2_t = total_h2[valid] / 1000.0              # metric tons
starts = total_starts[valid] if total_starts is not None else None

n = cost.size
print(f"Valid configurations: {n} of {total_h2.size}")

# Track where the default case lands after filtering.
default_valid_idx = None
if valid[DEFAULT_IDX]:
    default_valid_idx = int(np.sum(valid[:DEFAULT_IDX]))

# ==================================================
# 1. DESCRIPTIVE STATISTICS
# ==================================================

def describe(name, x, unit):
    print(f"\n  {name} ({unit})")
    print(f"    mean   {np.mean(x):8.3f}    std   {np.std(x, ddof=1):8.3f}")
    print(f"    min    {np.min(x):8.3f}    max   {np.max(x):8.3f}")
    q = np.percentile(x, [5, 25, 50, 75, 95])
    print(f"    p05 {q[0]:7.3f}  p25 {q[1]:7.3f}  p50 {q[2]:7.3f}"
          f"  p75 {q[3]:7.3f}  p95 {q[4]:7.3f}")

print("\n" + "=" * 60)
print("1. DESCRIPTIVE STATISTICS")
print("=" * 60)
describe("Cost per H2",  cost, "USD/kg")
describe("CO2 per H2",   co2,  "kg/kg")
describe("H2 produced",  h2_t, "t")
if starts is not None:
    describe("Startups", starts, "count")

# ==================================================
# 2. LINEAR COLLAPSE: OLS REGRESSION OF CO2 ON COST
# ==================================================

print("\n" + "=" * 60)
print("2. COST-CARBON LINEAR RELATIONSHIP (OLS: CO2 ~ cost)")
print("=" * 60)

reg = stats.linregress(cost, co2)
co2_pred = reg.intercept + reg.slope * cost
resid = co2 - co2_pred
rmse = np.sqrt(np.mean(resid ** 2))

pearson_r, pearson_p = stats.pearsonr(cost, co2)
spearman_r, spearman_p = stats.spearmanr(cost, co2)

print(f"  slope       {reg.slope:8.4f} (kg CO2/kg H2) per (USD/kg)")
print(f"  intercept   {reg.intercept:8.4f} kg CO2/kg H2")
print(f"  R^2         {reg.rvalue ** 2:8.4f}")
print(f"  RMSE        {rmse:8.4f} kg CO2/kg H2  (vertical scatter about line)")
print(f"  Pearson  r  {pearson_r:8.4f}  (p = {pearson_p:.2e})")
print(f"  Spearman r  {spearman_r:8.4f}  (p = {spearman_p:.2e})")
print(f"  slope 95% CI [{reg.slope - 1.96 * reg.stderr:.4f}, "
      f"{reg.slope + 1.96 * reg.stderr:.4f}]")

# ==================================================
# 3. PCA: VARIANCE EXPLAINED BY THE PRINCIPAL AXIS
# ==================================================
# A clean, scale-free way to express the "collapse onto a line": project the
# standardized (cost, CO2) cloud onto its principal axes and report how much
# variance the first axis captures. The perpendicular spread is the envelope
# half-width.

print("\n" + "=" * 60)
print("3. PRINCIPAL-AXIS ANALYSIS (envelope tightness)")
print("=" * 60)

X = np.column_stack([cost, co2])
mu = X.mean(axis=0)
Xc = X - mu

# Standardized PCA for the variance-explained metric (scale-independent).
Xs = Xc / X.std(axis=0, ddof=1)
cov_s = np.cov(Xs, rowvar=False)
eigval_s, _ = np.linalg.eigh(cov_s)
eigval_s = np.sort(eigval_s)[::-1]
var_explained = eigval_s[0] / eigval_s.sum()

# Unstandardized PCA in physical units for the projection and residual spread.
cov = np.cov(Xc, rowvar=False)
eigval, eigvec = np.linalg.eigh(cov)
order = np.argsort(eigval)[::-1]
eigval, eigvec = eigval[order], eigvec[:, order]
pc1, pc2 = eigvec[:, 0], eigvec[:, 1]

proj1 = Xc @ pc1          # position along the envelope
proj2 = Xc @ pc2          # perpendicular offset (envelope width)
perp_std = np.std(proj2, ddof=1)

print(f"  variance on principal axis   {var_explained * 100:6.2f} %")
print(f"  variance on minor axis       {(1 - var_explained) * 100:6.2f} %")
print(f"  principal-axis direction     dCO2/dcost = {pc1[1] / pc1[0]:.4f}")
print(f"  perpendicular spread (1 sigma) {perp_std:.4f}  (in mixed units)")
print(f"  total least-squares slope    {pc1[1] / pc1[0]:.4f} "
      f"(vs OLS slope {reg.slope:.4f})")

# ==================================================
# 4. PRODUCTION GRADIENT ALONG THE ENVELOPE
# ==================================================
# Fig. 10a shows production rising along the cost-carbon line. Quantify it:
# correlate H2 (and startups) with position along the principal axis.

print("\n" + "=" * 60)
print("4. PRODUCTION / CYCLING GRADIENT ALONG ENVELOPE")
print("=" * 60)

# Orient proj1 so that increasing proj1 means increasing cost.
if np.corrcoef(proj1, cost)[0, 1] < 0:
    proj1 = -proj1
    pc1 = -pc1

r_h2, p_h2 = stats.pearsonr(proj1, h2_t)
print(f"  H2 production vs envelope position   r = {r_h2:.4f} "
      f"(p = {p_h2:.2e})")
print(f"  H2 production vs cost/kg             r = "
      f"{stats.pearsonr(cost, h2_t)[0]:.4f}")
print(f"  H2 production vs CO2/kg              r = "
      f"{stats.pearsonr(co2, h2_t)[0]:.4f}")

if starts is not None:
    r_s, p_s = stats.pearsonr(proj1, starts)
    # Test for non-monotonic (peaked) startup behaviour: fit quadratic in
    # envelope position and check the curvature term.
    z = np.polyfit(proj1, starts, 2)
    print(f"  Startups vs envelope position       r = {r_s:.4f} "
          f"(p = {p_s:.2e})  [linear]")
    print(f"  Startups quadratic fit curvature    {z[0]:.4f} "
          f"({'concave / peaked' if z[0] < 0 else 'convex'})")

# ==================================================
# 5. BINNED ENVELOPE WIDTH
# ==================================================
# How tight is the band across the cost range? Report median CO2 and the
# interquartile spread of CO2 within cost bins.

print("\n" + "=" * 60)
print("5. ENVELOPE WIDTH BY COST BIN")
print("=" * 60)

edges = np.linspace(cost.min(), cost.max(), N_BINS + 1)
centers = 0.5 * (edges[:-1] + edges[1:])
med_co2 = np.full(N_BINS, np.nan)
iqr_co2 = np.full(N_BINS, np.nan)

print(f"  {'cost mid':>9}  {'n':>5}  {'med CO2':>8}  {'IQR CO2':>8}")
for i in range(N_BINS):
    m = (cost >= edges[i]) & (cost < edges[i + 1] if i < N_BINS - 1
                              else cost <= edges[i + 1])
    if m.sum() >= 5:
        med_co2[i] = np.median(co2[m])
        q75, q25 = np.percentile(co2[m], [75, 25])
        iqr_co2[i] = q75 - q25
        print(f"  {centers[i]:9.3f}  {m.sum():5d}  "
              f"{med_co2[i]:8.3f}  {iqr_co2[i]:8.3f}")

# ==================================================
# 6. SMR BENCHMARK CROSSING
# ==================================================

print("\n" + "=" * 60)
print("6. GREY-SMR BENCHMARK COMPARISON")
print("=" * 60)
print(f"  configs at/below SMR upper bound ({SMR_HIGH:g}): "
      f"{np.mean(co2 <= SMR_HIGH) * 100:5.2f} %")
print(f"  configs at/below SMR lower bound ({SMR_LOW:g}):  "
      f"{np.mean(co2 <= SMR_LOW) * 100:5.2f} %")
print(f"  minimum achievable CO2/H2:        {co2.min():.3f} kg/kg")

# ==================================================
# 7. DEFAULT CASE POSITION
# ==================================================

if default_valid_idx is not None:
    print("\n" + "=" * 60)
    print("7. DEFAULT CASE POSITION IN ENSEMBLE")
    print("=" * 60)
    di = default_valid_idx
    print(f"  cost/H2  {cost[di]:7.3f}  "
          f"(percentile {stats.percentileofscore(cost, cost[di]):5.1f})")
    print(f"  CO2/H2   {co2[di]:7.3f}  "
          f"(percentile {stats.percentileofscore(co2, co2[di]):5.1f})")
    print(f"  H2 prod  {h2_t[di]:7.3f}  "
          f"(percentile {stats.percentileofscore(h2_t, h2_t[di]):5.1f})")
    print(f"  residual from OLS line  {resid[di]:+.4f} kg/kg "
          f"({resid[di] / rmse:+.2f} sigma)")

# ==================================================
# FIGURE: FOUR-PANEL DIAGNOSTIC
# ==================================================

fig, axes = plt.subplots(2, 2, figsize=(11, 8))

# (a) scatter with OLS fit and +/- 2 RMSE band
ax = axes[0, 0]
ax.scatter(cost, co2, s=3, alpha=0.35, c=h2_t, cmap="viridis",
           edgecolors="none")
xs = np.linspace(cost.min(), cost.max(), 200)
ax.plot(xs, reg.intercept + reg.slope * xs, "k-", lw=1.5,
        label=f"OLS  $R^2$={reg.rvalue**2:.3f}")
ax.fill_between(xs, reg.intercept + reg.slope * xs - 2 * rmse,
                reg.intercept + reg.slope * xs + 2 * rmse,
                color="k", alpha=0.10, label=r"$\pm 2$ RMSE")
ax.axhspan(SMR_LOW, SMR_HIGH, color="red", alpha=0.12, label="Grey SMR")
if default_valid_idx is not None:
    ax.scatter(cost[default_valid_idx], co2[default_valid_idx], marker="X",
               s=120, facecolors="white", edgecolors="black", linewidths=1.5,
               zorder=5, label="Default")
ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)")
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)")
ax.set_title("(a) Cost-carbon envelope with OLS fit")
ax.legend(fontsize=9, frameon=True)
ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# (b) residuals about the fit line
ax = axes[0, 1]
ax.scatter(cost, resid, s=3, alpha=0.35, color="#1A3E6E", edgecolors="none")
ax.axhline(0, color="k", lw=1)
ax.axhline(2 * rmse, color="k", ls="--", lw=0.8)
ax.axhline(-2 * rmse, color="k", ls="--", lw=0.8)
ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)")
ax.set_ylabel("Residual CO$_2$/H$_2$ (kg/kg)")
ax.set_title(f"(b) Residuals about fit (RMSE = {rmse:.3f})")
ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# (c) production gradient along principal axis
ax = axes[1, 0]
ax.scatter(proj1, h2_t, s=3, alpha=0.35, color="#1D5C1A", edgecolors="none")
ax.set_xlabel("Position along principal axis (PC1)")
ax.set_ylabel("H$_2$ Produced (t)")
ax.set_title(f"(c) Production gradient (r = {r_h2:.3f})")
ax.grid(alpha=0.25)
ax.set_axisbelow(True)

# (d) binned envelope width
ax = axes[1, 1]
ax.plot(centers, med_co2, "o-", color="#1A1916", lw=1.2, ms=4,
        label="median CO$_2$/H$_2$")
ax.fill_between(centers, med_co2 - iqr_co2 / 2, med_co2 + iqr_co2 / 2,
                color="#7A4D00", alpha=0.20, label="IQR band")
ax.set_xlabel("Electricity Cost per H$_2$ (USD/kg)")
ax.set_ylabel("CO$_2$ per H$_2$ (kg/kg)")
ax.set_title("(d) Envelope width by cost bin")
ax.legend(fontsize=9, frameon=True)
ax.grid(alpha=0.25)
ax.set_axisbelow(True)

fig.tight_layout()
fig.savefig(SAVE_FIG, dpi=300, bbox_inches="tight")
print(f"\nFigure saved: {SAVE_FIG}")
plt.show()