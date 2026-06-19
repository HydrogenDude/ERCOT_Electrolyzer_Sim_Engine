import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

# --------- LOAD DATA ---------
file_path = "data/inputs/ERCOT_2020_2025.xlsx"
df = pd.read_excel(file_path, engine="openpyxl")

df.columns = df.columns.str.strip()
df["Time"] = pd.to_datetime(df["Time"])

# --------- FILTER ---------
start = "2025-04-16 00:00"
end = "2025-04-20 17:00"

df = df[(df["Time"] >= start) & (df["Time"] <= end)]

times = df["Time"]
price = df["Price"]
clean_ratio = df["Clean Ratio"]

# --------- STYLE ---------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 12,
})

# =========================================================
# PRICE PLOT
# =========================================================
fig, ax = plt.subplots(figsize=(4, 3))

ax.fill_between(times, price, color="#1f77b4", alpha=0.70)
ax.plot(times, price, color="#1f77b4", linewidth=1.5, alpha=0.70)

# Threshold lines (colored)
ax.axhline(30, color="green", linewidth=2)        # START
ax.axhline(50, color="goldenrod", linewidth=2)    # TURNDOWN
ax.axhline(55, color="red", linewidth=2.5)        # STOP

ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

ax.set_ylabel("Electricity Price", fontsize=14)

plt.margins(x=0)
plt.tight_layout()
plt.show()


# =========================================================
# CLEAN RATIO PLOT
# =========================================================
fig, ax = plt.subplots(figsize=(4, 3))

ax.fill_between(times, clean_ratio, color="#892ca0", alpha=0.70)
ax.plot(times, clean_ratio, color="#892ca0", linewidth=1.5, alpha=0.70)

# Threshold lines (colored)
ax.axhline(0.60, color="green", linewidth=2)      # START
ax.axhline(0.50, color="goldenrod", linewidth=2)  # TURNDOWN
ax.axhline(0.40, color="red", linewidth=2.5)      # STOP

ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

ax.set_ylabel("Clean Energy Ratio", fontsize=14)

plt.margins(x=0)
plt.tight_layout()
plt.show()


# =========================================================
# SEPARATE LEGEND FIGURE
# =========================================================
fig, ax = plt.subplots(figsize=(6, 2))

# Create custom legend handles
start_line = mlines.Line2D([], [], color='green', linewidth=2, label='START')
turndown_line = mlines.Line2D([], [], color='goldenrod', linewidth=2, label='TURNDOWN')
stop_line = mlines.Line2D([], [], color='red', linewidth=2.5, label='STOP')


# Add legend
ax.legend(handles=[start_line, turndown_line, stop_line],
          loc='center',
          frameon=False,
          fontsize=14,
          ncol=3)

# Remove axes
ax.axis('off')

plt.tight_layout()
plt.show()