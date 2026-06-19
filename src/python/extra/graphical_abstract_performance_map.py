import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

frac = np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

pdc   = np.array([15.6, 20.8, 26.0, 31.2, 36.4, 41.6, 46.8, 52.0])
psmps = np.array([17.4, 22.8, 28.3, 33.9, 39.4, 44.9, 50.4, 55.9])
ptot  = np.array([36.4, 41.8, 47.3, 52.9, 58.4, 63.9, 69.4, 74.9])

mh2g  = np.array([0.32, 0.40, 0.49, 0.58, 0.66, 0.73, 0.82, 0.89])
mh2n  = np.array([0.19, 0.29, 0.37, 0.45, 0.55, 0.62, 0.70, 0.77])

x_fine = np.linspace(frac.min(), frac.max(), 400)

power_series = [
    (ptot,  r"$P_{ac,total}$",  "#9FD0EE"),
    (psmps, r"$P_{ac,smps}$",   "#4FA3D8"),
    (pdc,   r"$P_{dc,stack}$",  "#0B4A85"),
]
flow_series = [
    (mh2g, r"$\dot{m}_{H_2,gross}$", "#F2B27A"),
    (mh2n, r"$\dot{m}_{H_2,net}$",   "#C8401A"),
]

plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax1 = plt.subplots(figsize=(3, 3))
ax2 = ax1.twinx()
fig.patch.set_alpha(0)
ax1.patch.set_alpha(0)

pchip = {}
for data, label, color in power_series + flow_series:
    pchip[label] = PchipInterpolator(frac, data)(x_fine)

# loss bands: gap between successive series carries physical meaning
ax1.fill_between(x_fine, pchip[r"$P_{dc,stack}$"], pchip[r"$P_{ac,smps}$"],
                  color="#4FA3D8", alpha=0.22, zorder=1)
ax1.fill_between(x_fine, pchip[r"$P_{ac,smps}$"], pchip[r"$P_{ac,total}$"],
                  color="#9FD0EE", alpha=0.30, zorder=1)
ax2.fill_between(x_fine, pchip[r"$\dot{m}_{H_2,net}$"], pchip[r"$\dot{m}_{H_2,gross}$"],
                  color="#F2B27A", alpha=0.35, zorder=1)

p_handles, f_handles = [], []
for data, label, color in power_series:
    line, = ax1.plot(x_fine, pchip[label], color=color, lw=2.6, zorder=3,
                      solid_capstyle="round", label=label)
    ax1.scatter(frac, data, s=30, facecolor=color, edgecolor="white",
                linewidth=1.1, zorder=4)
    p_handles.append(line)

for data, label, color in flow_series:
    line, = ax2.plot(x_fine, pchip[label], color=color, lw=2.6, zorder=3,
                      solid_capstyle="round", label=label)
    ax2.scatter(frac, data, s=30, facecolor=color, edgecolor="white",
                linewidth=1.1, zorder=4)
    f_handles.append(line)

for ax in (ax1, ax2):
    ax.tick_params(left=False, right=False, bottom=False,
                    labelleft=False, labelright=False, labelbottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylim(bottom=0)

ax1.set_xlabel("Stack load fraction", fontsize=15, labelpad=4, color="#333333")
ax1.set_ylabel("Power", fontsize=15, labelpad=8, color="#0B4A85")
ax2.set_ylabel("H$_2$ flow rate", fontsize=15, labelpad=8, color="#C8401A")

#leg = fig.legend(p_handles + f_handles,
#                  [h.get_label() for h in p_handles + f_handles],
#                  loc="upper center", bbox_to_anchor=(0.5, 1.04),
#                  ncol=5, frameon=False, fontsize=11.5,
#                  handlelength=1.6, handletextpad=0.5, columnspacing=1.4)

fig.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()