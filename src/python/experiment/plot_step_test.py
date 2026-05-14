import matplotlib.pyplot as plt
import numpy as np

# =========================================================
# Matplotlib style (MATCHES hydrogen plots)
# =========================================================
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "legend.fontsize": 12,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "lines.linewidth": 2.5,
})

# =========================================================
# Step profile data
# =========================================================
x = np.array([0, 1, 2, 4, 9, 9, 10, 40, 70, 100, 130, 160, 190, 220, 250])
y = np.array([0, 0, 10, 20, 20, 58, 100, 90, 80, 70, 60, 50, 40, 30, 0])

# =========================================================
# Figure (same aspect logic as hydrogen plots)
# =========================================================
fig, ax = plt.subplots(figsize=(7, 4))

# =========================================================
# Step command profile
# =========================================================
ax.step(
    x,
    y,
    where="post",
    color="black",
    linewidth=2.5,
    label="Command profile"
)

# =========================================================
# Turn‑down limit
# =========================================================
ax.hlines(
    30,
    xmin=0,
    xmax=260,
    colors="red",
    linestyles="dashed",
    linewidth=2.5,
    label="Turn‑down limit"
)

#ax.annotate(
#    "Turn‑down limit",
#    xy=(45, 30),
#    xytext=(0, 6),
#    textcoords="offset points",
#    ha="left",
#    va="bottom",
#    fontsize=10,
#    color="red",
#    fontweight="bold"
#)

# =========================================================
# Axes formatting (hydrogen‑style)
# =========================================================
ax.set_xlabel("Time (minutes)")
ax.set_ylabel("Stack Load (%)")

ax.set_xlim(0, 260)
ax.set_ylim(0, 110)

ax.set_xticks([0, 50, 100, 150, 200, 250])
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, alpha=0.25)

# Light, consistent spines
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

ax.tick_params(axis="both", which="major", length=6, width=1)

# =========================================================
# Legend (consistent placement)
# =========================================================
ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, 0.02),
    ncol=2,
    frameon=True,
    handlelength=2.0,
    handletextpad=0.6
)

# =========================================================
# Save / show
# =========================================================
fig.tight_layout()
fig.savefig("step_test_command_profile.pdf", bbox_inches="tight")
plt.show()