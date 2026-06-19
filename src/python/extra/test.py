import h5py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mpath
from scipy.spatial import Delaunay, cKDTree
from scipy.ndimage import gaussian_filter
from collections import defaultdict

# ==================================================
# SETTINGS (same as main script, kept consistent)
# ==================================================

GRID_RES          = 400   # lower than main script for fast iteration
ALPHA_SHAPE_R     = 0.05
BOUNDARY_SMOOTH   = 10
ALPHA_K_NEIGHBORS = 5

# Candidate ALPHA_DIST_SCALE values to compare side by side.
# Edit this list after looking at the percentile printout below.
CANDIDATE_SCALES = [0.05, 0.02, 0.01, 0.005, 0.002, 0.001]

# ==================================================
# LOAD DATA
# ==================================================

H5_PATH = r"C:/Users/evan123/Desktop/large_sim_results/N10000_S69_Doff_2025.h5"

with h5py.File(H5_PATH, "r") as f:
    total_cost = f["totals/total_cost"][:].ravel()
    total_co2  = f["totals/total_co2_kg"][:].ravel()
    total_h2   = f["totals/total_h2_kg"][:].ravel()

valid       = total_h2 > 1e-6
cost_per_h2 = total_cost[valid] / total_h2[valid]
co2_per_h2  = total_co2[valid]  / total_h2[valid]

# ==================================================
# AXIS LIMITS (same as main script)
# ==================================================

x_min, x_max = 0.0, 3.0
y_min, y_max = 10.0, 35.0

in_range = ((cost_per_h2 >= x_min) & (cost_per_h2 <= x_max) &
            (co2_per_h2  >= y_min) & (co2_per_h2  <= y_max))
x = cost_per_h2[in_range]
y = co2_per_h2[in_range]

print(f"Number of points in range: {len(x)}")

# ==================================================
# NORMALIZE TO [0,1]
# ==================================================

def norm_coords(vals, vmin, vmax):
    return (vals - vmin) / (vmax - vmin)

xn = norm_coords(x, x_min, x_max)
yn = norm_coords(y, y_min, y_max)
pts2d = np.stack([xn, yn], axis=1)

# ==================================================
# NEAREST-NEIGHBOR DISTANCE DIAGNOSTIC
# This is the key measurement: it tells you the real
# spacing scale in normalized coordinates, so you can
# set ALPHA_DIST_SCALE based on data rather than guessing.
# ==================================================

tree = cKDTree(pts2d)
nn_dists_self, _ = tree.query(pts2d, k=ALPHA_K_NEIGHBORS + 1)  # +1: includes self at k=0
nn_dists_self = nn_dists_self[:, 1:]  # drop self-distance column
mean_nn_self = nn_dists_self.mean(axis=1)

print("\nPercentiles of mean nearest-neighbor distance (point-to-point):")
for p in [5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  {p:>3}th percentile: {np.percentile(mean_nn_self, p):.6f}")

print(f"\n  min:  {mean_nn_self.min():.6f}")
print(f"  max:  {mean_nn_self.max():.6f}")
print(f"  mean: {mean_nn_self.mean():.6f}")

# ==================================================
# ALPHA SHAPE MASK (same logic as main script)
# Computed once, reused across all candidate scales.
# ==================================================

def circumradius(p1, p2, p3):
    a = np.linalg.norm(p2 - p1)
    b = np.linalg.norm(p3 - p2)
    c = np.linalg.norm(p1 - p3)
    s = (a + b + c) / 2
    area = np.sqrt(np.maximum(s*(s-a)*(s-b)*(s-c), 0))
    return (a * b * c) / (4 * area + 1e-12)

tri = Delaunay(pts2d)

kept_triangles = []
for simplex in tri.simplices:
    p1, p2, p3 = pts2d[simplex]
    if circumradius(p1, p2, p3) < ALPHA_SHAPE_R:
        kept_triangles.append(simplex)

edge_count = defaultdict(int)
for tri_idx in kept_triangles:
    for i in range(3):
        edge = tuple(sorted([tri_idx[i], tri_idx[(i+1) % 3]]))
        edge_count[edge] += 1

boundary_edges = [e for e, count in edge_count.items() if count == 1]

def build_polygon(edges):
    edge_map = defaultdict(list)
    for a, b in edges:
        edge_map[a].append(b)
        edge_map[b].append(a)

    start   = edges[0][0]
    polygon = [start]
    prev    = None
    current = start

    while True:
        neighbors = edge_map[current]
        next_pt   = None
        for nb in neighbors:
            if nb != prev:
                next_pt = nb
                break
        if next_pt is None or next_pt == start:
            break
        polygon.append(next_pt)
        prev, current = current, next_pt

    return np.array(polygon)

poly_idx = build_polygon(boundary_edges)
poly_pts = pts2d[poly_idx]

gx = np.linspace(0, 1, GRID_RES)
gy = np.linspace(0, 1, GRID_RES)
GX, GY    = np.meshgrid(gx, gy)
grid_flat = np.stack([GX.ravel(), GY.ravel()], axis=1)

path   = mpath.Path(poly_pts)
inside = path.contains_points(grid_flat).reshape(GRID_RES, GRID_RES)

inside_smooth = gaussian_filter(inside.astype(float), sigma=BOUNDARY_SMOOTH)
boundary_mask = (inside_smooth > 0.5).astype(float)

# ==================================================
# GRID-TO-DATA NEAREST-NEIGHBOR DISTANCES
# Computed once; reused for every candidate scale.
# ==================================================

nn_dists_grid, _ = tree.query(grid_flat, k=ALPHA_K_NEIGHBORS)
nn_dists_grid = np.atleast_2d(nn_dists_grid.T).T
mean_nn_grid = nn_dists_grid.mean(axis=1).reshape(GRID_RES, GRID_RES)

print(f"\nPercentiles of mean nearest-neighbor distance (grid-to-point, inside boundary only):")
inside_vals = mean_nn_grid[boundary_mask > 0.5]
for p in [5, 25, 50, 75, 95]:
    print(f"  {p:>3}th percentile: {np.percentile(inside_vals, p):.6f}")

# ==================================================
# RENDER CANDIDATE ALPHA MAPS SIDE BY SIDE
# ==================================================

n = len(CANDIDATE_SCALES)
ncols = 3
nrows = int(np.ceil(n / ncols))

fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3.2 * nrows))
axes = np.atleast_1d(axes).ravel()

for i, scale in enumerate(CANDIDATE_SCALES):
    density_alpha = np.exp(-(mean_nn_grid ** 2) / (2 * scale ** 2))
    combined_alpha = boundary_mask * density_alpha

    ax = axes[i]
    # Render alpha as grayscale: white = alpha 1 (dense), black = alpha 0 (sparse/outside)
    ax.imshow(
        combined_alpha,
        extent=[x_min, x_max, y_min, y_max],
        origin="lower",
        aspect="auto",
        cmap="gray",
        vmin=0, vmax=1
    )
    ax.set_title(f"ALPHA_DIST_SCALE = {scale}", fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])

# hide unused axes
for j in range(n, len(axes)):
    axes[j].axis("off")

fig.suptitle(
    "Alpha map preview (white = opaque, black = fully faded)\n"
    "Pick the smallest scale that still preserves the band's interior",
    fontsize=11
)
plt.tight_layout()
plt.show()