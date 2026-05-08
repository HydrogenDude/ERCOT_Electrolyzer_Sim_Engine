import numpy as np
import pandas as pd
from pathlib import Path
import argparse


# ==========================================================
# Project path resolution
# ==========================================================
def get_project_root() -> Path:
    """
    Resolve the project root directory based on this file location.

    Expected location:
        src/python/case_generation/<this_file>.py

    Returns:
        Path to repository root.
    """
    return Path(__file__).resolve().parents[3]


# ==========================================================
# DOE generator (controls only)
# ==========================================================
def generate_electrolyzer_control_cases(N: int, seed: int = 1) -> pd.DataFrame:
    """
    Space-filling, constraint-correct DOE for electrolyzer supervisory control.

    Guarantees (row-wise, by construction):
      clean_ratio_stop < clean_ratio_turndown < clean_ratio_start
      price_start < price_turndown < price_stop
    """

    if N < 10:
        raise ValueError("N must be >= 10 for meaningful stratification")

    rng = np.random.default_rng(seed)
    bounds = control_parameter_bounds()

    CLEAN_RATIO_GAP = 1e-3
    PRICE_GAP = 1e-2

    rows = []

    for i in range(1, N + 1):

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

        rows.append(
            {
                "ID": i,
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
            }
        )

    T = pd.DataFrame(rows)

    # Decorrelate discrete parameters only
    perm = rng.permutation(N)
    cols = [
        "min_up_steps", "min_down_steps",
        "turndown_delay", "recover_delay", "price_delay"
    ]
    T[cols] = T.loc[perm, cols].values

    return T


# ==========================================================
# Parameter bounds
# ==========================================================
def control_parameter_bounds():
    return {
        "min_up_steps_max": 8,
        "min_down_steps_max": 6,
        "turndown_delay_max": 4,
        "recover_delay_max": 4,
        "price_delay_max": 4,
        "clean_ratio_start": (0.5, 0.8),
        "clean_ratio_stop": 0.20,
        "price_start": (15, 80),
        "price_stop": 100,
    }


# ==========================================================
# CLI entry point
# ==========================================================
def main():
    parser = argparse.ArgumentParser(
        description="Generate electrolyzer supervisory control DOE cases."
    )
    parser.add_argument("--N", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--filename",
        type=str,
        default="electrolyzer_control_cases.csv",
        help="Output CSV filename (written to configs/paper_cases/)",
    )

    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = project_root / "configs" / "paper_cases"
    output_dir.mkdir(parents=True, exist_ok=True)

    outfile = output_dir / args.filename

    T = generate_electrolyzer_control_cases(args.N, args.seed)
    T.to_csv(outfile, index=False)

    print(f"[OK] Generated {len(T)} control cases")
    print(f"[OK] Written to: {outfile}")


if __name__ == "__main__":
    main()