import numpy as np
import pandas as pd
from pathlib import Path
import argparse

# ==========================================================
# Similarity thresholds (EDIT THESE)
# ==========================================================
PRICE_TOL = 5.0        # $/MWh
CR_TOL = 0.05         # clean ratio (unitless)

# ==========================================================
# Project path resolution
# ==========================================================
def get_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent
    raise RuntimeError("Project root not found.")

# ==========================================================
# Default supervisory control case (ALWAYS ID = 1)
# ==========================================================
"""
def default_supervisory_control_case() -> pd.DataFrame:
    row = {
        "ID": 1,
        "min_up_steps": 4,
        "min_down_steps": 2,
        "price_start": 30.0,
        "price_turndown": 50.0,
        "price_stop": 55.0,
        "clean_ratio_start": 0.60,
        "clean_ratio_turndown": 0.50,
        "clean_ratio_stop": 0.40,
        "turndown_delay": 2,
        "recover_delay": 4,
        "price_delay": 2,
    }
    return pd.DataFrame([row])
"""


def default_supervisory_control_case() -> pd.DataFrame:
    row = {
        "ID": 1,
        "min_up_steps": 0,
        "min_down_steps": 0,
        "price_start": 30.0,
        "price_turndown": 50.0,
        "price_stop": 55.0,
        "clean_ratio_start": 0.75,
        "clean_ratio_turndown": 0.70,
        "clean_ratio_stop": 0.65,
        "turndown_delay": 0,
        "recover_delay": 0,
        "price_delay": 0,
    }
    return pd.DataFrame([row])

    
# ==========================================================
# Generate supervisory control cases
# ==========================================================
def generate_supervisory_control_cases(N: int, seed: int = 1) -> pd.DataFrame:
    if N < 1:
        raise ValueError("N must be >= 1")

    rng = np.random.default_rng(seed)
    bounds = control_parameter_bounds()

    CLEAN_RATIO_GAP = 0.05
    PRICE_GAP = 5.0

    rows = [default_supervisory_control_case().iloc[0].to_dict()]

    for case_id in range(2, N + 1):
        min_up_steps = rng.integers(0, bounds["min_up_steps_max"] + 1)
        min_down_steps = rng.integers(0, bounds["min_down_steps_max"] + 1)

        turndown_delay = rng.integers(0, bounds["turndown_delay_max"] + 1)
        recover_delay = rng.integers(0, bounds["recover_delay_max"] + 1)
        price_delay = rng.integers(0, bounds["price_delay_max"] + 1)

        clean_ratio_start = rng.uniform(*bounds["clean_ratio_start"])
        clean_ratio_stop = rng.uniform(
            bounds["clean_ratio_stop"],
            clean_ratio_start - 2 * CLEAN_RATIO_GAP,
        )
        clean_ratio_turndown = rng.uniform(
            clean_ratio_stop + CLEAN_RATIO_GAP,
            clean_ratio_start - CLEAN_RATIO_GAP,
        )

        price_start = rng.uniform(*bounds["price_start"])
        price_stop = rng.uniform(
            price_start + 2 * PRICE_GAP,
            bounds["price_stop"],
        )
        price_turndown = rng.uniform(
            price_start + PRICE_GAP,
            price_stop - PRICE_GAP,
        )

        rows.append({
            "ID": case_id,
            "min_up_steps": min_up_steps,
            "min_down_steps": min_down_steps,
            "price_start": price_start,
            "price_turndown": price_turndown,
            "price_stop": price_stop,
            "clean_ratio_start": clean_ratio_start,
            "clean_ratio_turndown": clean_ratio_turndown,
            "clean_ratio_stop": clean_ratio_stop,
            "turndown_delay": turndown_delay,
            "recover_delay": recover_delay,
            "price_delay": price_delay,
        })

    return pd.DataFrame(rows)

# ==========================================================
# Similarity filtering
# ==========================================================
def prune_similar_cases(T: pd.DataFrame) -> pd.DataFrame:
    keep = []
    removed = 0

    for _, row in T.iterrows():
        if row["ID"] == 1:
            keep.append(row)
            continue

        is_duplicate = False
        for k in keep:
            if (
                abs(row["price_start"] - k["price_start"]) < PRICE_TOL and
                abs(row["price_turndown"] - k["price_turndown"]) < PRICE_TOL and
                abs(row["price_stop"] - k["price_stop"]) < PRICE_TOL and
                abs(row["clean_ratio_start"] - k["clean_ratio_start"]) < CR_TOL and
                abs(row["clean_ratio_turndown"] - k["clean_ratio_turndown"]) < CR_TOL and
                abs(row["clean_ratio_stop"] - k["clean_ratio_stop"]) < CR_TOL
            ):
                is_duplicate = True
                removed += 1
                break

        if not is_duplicate:
            keep.append(row)

    T_filt = pd.DataFrame(keep).reset_index(drop=True)
    T_filt["ID"] = np.arange(1, len(T_filt) + 1)

    print(f"[INFO] Similarity pruning removed {removed} cases")
    print(f"[INFO] Final DOE size: {len(T_filt)}")

    return T_filt

# ==========================================================
# Parameter bounds
# ==========================================================
def control_parameter_bounds():
    return {
        "min_up_steps_max": 8,
        "min_down_steps_max": 8,
        "turndown_delay_max": 8,
        "recover_delay_max": 8,
        "price_delay_max": 8,
        "clean_ratio_start": (0.5, 0.8),
        "clean_ratio_stop": 0.20,
        "price_start": (15, 80),
        "price_stop": 100,
    }

# ==========================================================
# CLI entry point
# ==========================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int, default=1)
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--filename", type=str, default="supervisory_control_cases.csv")
    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = project_root / "configs" / "paper_cases"
    output_dir.mkdir(parents=True, exist_ok=True)

    T = generate_supervisory_control_cases(args.N, seed=args.seed)
    T = prune_similar_cases(T)

    outfile = output_dir / args.filename
    T.to_csv(outfile, index=False)

    print(f"[OK] Written to: {outfile}")

if __name__ == "__main__":
    main()