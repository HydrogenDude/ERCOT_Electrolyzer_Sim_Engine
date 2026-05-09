import numpy as np
import pandas as pd
from pathlib import Path
import argparse


# ==========================================================
# Project path resolution
# ==========================================================
def get_project_root() -> Path:
    """
    Resolve project root using an explicit '.project-root' marker file.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".project-root").exists():
            return parent

    raise RuntimeError(
        "Project root not found. Missing '.project-root' marker."
    )


# ==========================================================
# Default supervisory control case
# ==========================================================
def default_supervisory_control_case() -> pd.DataFrame:
    """
    Deterministic default supervisory control case.

    Used when N == 0 to allow single-case simulations without DOE.
    Values are chosen to be:
      - physically reasonable
      - non-extreme
      - strictly monotonic and constraint-safe
    """

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


# ==========================================================
# DOE generator (controls only)
# ==========================================================
def generate_supervisory_control_cases(N: int, seed: int = 1) -> pd.DataFrame:
    """
    Space-filling, constraint-correct DOE for electrolyzer
    supervisory control.

    Guarantees (row-wise, by construction):
      clean_ratio_stop < clean_ratio_turndown < clean_ratio_start
      price_start < price_turndown < price_stop

    Special behavior:
      - If N == 0, returns a single deterministic default case.
    """

    # ------------------------------
    # Default-case override
    # ------------------------------
    if N == 0:
        return default_supervisory_control_case()

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

    # ------------------------------------------------------
    # Decorrelate discrete parameters (DOE hygiene)
    # ------------------------------------------------------
    perm = rng.permutation(N)
    cols = [
        "min_up_steps",
        "min_down_steps",
        "turndown_delay",
        "recover_delay",
        "price_delay",
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
    parser.add_argument("--N", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument(
        "--filename",
        type=str,
        default="supervisory_control_cases.csv",
        help="Output CSV filename (written to configs/paper_cases/)",
    )

    args = parser.parse_args()

    project_root = get_project_root()
    output_dir = project_root / "configs" / "paper_cases"
    output_dir.mkdir(parents=True, exist_ok=True)

    outfile = output_dir / args.filename

    T = generate_supervisory_control_cases(args.N, args.seed)
    T.to_csv(outfile, index=False)

    if args.N == 0:
        print("[INFO] N = 0 → using single default supervisory control case")

    print(f"[OK] Generated {len(T)} control case(s)")
    print(f"[OK] Written to: {outfile}")


if __name__ == "__main__":
    main()