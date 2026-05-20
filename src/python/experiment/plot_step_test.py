import matplotlib.pyplot as plt
import numpy as np
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
# Figure
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

# =========================================================
# Axes formatting
# =========================================================
ax.set_xlabel("Time (minutes)")
ax.set_ylabel("Stack Load (%)")

ax.set_xlim(0, 260)
ax.set_ylim(0, 110)

ax.set_xticks([0, 50, 100, 150, 200, 250])
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, alpha=0.25)

# Light spines
for spine in ax.spines.values():
    spine.set_linewidth(1.0)

ax.tick_params(axis="both", which="major", length=6, width=1)

# =========================================================
# Legend
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
# Save
# =========================================================
filename = "step_test_command_profile.pdf"
output_path = OUTPUT_DIR / filename

fig.tight_layout()
fig.savefig(output_path, format="pdf", bbox_inches="tight")

print(f"✅ Saved figure to: {output_path}")

plt.show()