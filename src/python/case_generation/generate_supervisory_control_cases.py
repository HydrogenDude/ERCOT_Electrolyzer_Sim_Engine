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
# Default supervisory control case (ALWAYS ID = 1)
# ==========================================================
def default_supervisory_control_case() -> pd.DataFrame:
    """
    Deterministic baseline supervisory control case.
    This case is ALWAYS ID = 1 and is NEVER generated stochastically.
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
def generate_supervisory_control_cases(
    N: int,
    seed: int = 1,
) -> pd.DataFrame:
    """
    Space-filling, constraint-correct DOE for electrolyzer supervisory control.

    Semantics:
      - ID = 1 is ALWAYS the deterministic default case.
      - N is the TOTAL number of cases returned.
      - If N = 1 → default case only.
      - If N > 1 → default + (N-1) stochastic cases.

    Guarantees (row-wise, by construction):
      clean_ratio_stop < clean_ratio_turndown < clean_ratio_start
      price_start < price_turndown < price_stop
    """

    if N < 1:
        raise ValueError("N must be >= 1")

    rng = np.random.default_rng(seed)
    bounds = control_parameter_bounds()

    CLEAN_RATIO_GAP = 0.05 #1e-3
    PRICE_GAP = 5.0 #1e-2

    # ------------------------------------------------------
    # Always start with default case
    # ------------------------------------------------------
    rows = [default_supervisory_control_case().iloc[0].to_dict()]

    # ------------------------------------------------------
    # Generate N-1 stochastic cases
    # ------------------------------------------------------
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

        rows.append(
            {
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
            }
        )

    T = pd.DataFrame(rows)

    # ------------------------------------------------------
    # Decorrelate discrete parameters (DOE hygiene)
    # (applies only to stochastic cases, not default)
    # ------------------------------------------------------
    if N > 1:
        discrete_cols = [
            "min_up_steps",
            "min_down_steps",
            "turndown_delay",
            "recover_delay",
            "price_delay",
        ]

        perm = rng.permutation(len(T) - 1) + 1  # skip ID=1
        T.loc[1:, discrete_cols] = T.loc[perm, discrete_cols].values

    return T


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
    parser = argparse.ArgumentParser(
        description="Generate electrolyzer supervisory control cases."
    )
    parser.add_argument("--N", type=int, default=10)
    parser.add_argument("--seed", type=int, default=69)
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

    T = generate_supervisory_control_cases(
        args.N,
        seed=args.seed,
    )

    T.to_csv(outfile, index=False)

    print("[INFO] Default case is always ID = 1")
    print(f"[OK] Generated {len(T)} total control case(s)")
    print(f"[OK] Written to: {outfile}")


if __name__ == "__main__":
    main()