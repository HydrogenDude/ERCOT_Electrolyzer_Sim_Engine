import pandas as pd
import matplotlib.pyplot as plt

# --------- LOAD DATA ---------
file_path = "outputs/tables/default_case_timeseries.csv"
df = pd.read_csv(file_path)

df.columns = df.columns.str.strip()
df["time"] = pd.to_datetime(df["time"])

# --------- FILTER ---------
start = "2025-04-16 00:00"
end = "2025-04-20 17:00"

df = df[(df["time"] >= start) & (df["time"] <= end)]

times = df["time"]
system_power = df["System Power (kW)"]

# --------- STYLE ---------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 12,
})

# =========================================================
# SYSTEM POWER PLOT
# =========================================================
fig, ax = plt.subplots(figsize=(4, 5))

ax.fill_between(times, system_power, color="#e27611", alpha=0.70)
ax.plot(times, system_power, color="#e27611", linewidth=1.5, alpha=0.70)

# Optional reference lines (uncomment / adjust if useful)
# ax.axhline(0, color="black", linewidth=1.5)

ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

ax.set_ylabel("System Power", fontsize=14)

plt.margins(x=0)
plt.tight_layout()
plt.show()
