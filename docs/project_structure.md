Each top-level directory has a single, well-defined responsibility,
described below.

---

## `configs/` — Simulation, Experiment, and Tool Configuration

The `configs/` directory contains all configuration information that
defines **what actions are performed**, independently of the code that
executes them.

Changing files here alters *what is run or generated*, not *how it is
implemented*.

### Subdirectories

- **`system/`**  
  Global system-level configuration, such as:
  - electrolyzer system parameters
  - time resolution and simulation horizon
  - fixed modeling assumptions

- **`scenarios/`**  
  Definitions of operating or grid scenarios, such as:
  - renewable penetration levels
  - price regimes
  - stress-test or extreme-event cases

- **`paper_cases/`**  
  Configuration sets used specifically for results reported in the paper.
  These cases are typically generated deterministically (e.g. via Python)
  and consumed by the simulation engine.  
  Files in this directory should be stable, versioned, and directly
  referenced by reproduction scripts.

- **`tools/`**  
  Configuration files controlling the behavior of auxiliary tools
  (e.g. formatting or export utilities).  
  These files define *what the tool acts on*, not *how the tool works*.

**Guiding rule:**  
If changing a value alters *what experiment or auxiliary action is being
performed*, it belongs in `configs/`.

---

## `data/` — Model Input Data

The `data/` directory stores **external input data consumed by the
simulation**, distinct from configuration and output artifacts.

### Subdirectories

- **`inputs/`**  
  Input datasets used by the simulation, such as:
  - grid demand or generation profiles
  - price signals
  - representative or downsampled time series

Large raw data archives or proprietary datasets should generally **not**
be committed. This directory should contain only the minimum data
required to reproduce published results or to run example cases.

---

## `docs/` — Project Documentation

The `docs/` directory contains documentation describing project
organization, design intent, and development workflows.

### Subdirectories

- **`design/`**  
  Formal design specifications and invariant descriptions that define
  implementation-independent logic, such as:
  - supervisory control invariants
  - parameter ordering and hysteresis rules
  - system-level design constraints

- **`workflows/`**  
  Documentation covering development and analysis workflows, such as:
  - git usage and branching conventions
  - repeatable simulation and analysis procedures

This directory documents *how the project is structured and developed*,
not the simulation code itself.

---

## `src/` — Core Implementation

The `src/` directory contains the implementation of the simulation engine
and tightly coupled supporting code.

Code here defines **how the model operates**, including:
- time-stepping logic,
- electrolyzer state machines,
- controller behavior,
- and supporting numerical or physical models.

### Subdirectories

- **`matlab/`**  
  MATLAB-based implementation of the simulation engine and associated
  model components.

- **`python/`**  
  Python code that is part of the core workflow, such as deterministic
  generation of simulation configuration inputs or closely coupled
  preprocessing.

**Boundary rule:**  
Code in `src/` directly affects model behavior. General-purpose utilities
that do not affect simulation behavior belong in `tools/`.

---

## `outputs/` — Generated Artifacts

The `outputs/` directory stores artifacts produced by simulations or
post-processing. These files are typically not tracked by git and can
always be regenerated.

### Subdirectories

- **`results/`** — numerical simulation outputs  
- **`figures/`** — plots and visualizations  
- **`tables/`** — aggregated or summary data tables  

Empty directories may be preserved using placeholder files (e.g.
`.gitkeep`) to maintain structure.

---

## `scripts/` — User-Facing Entry Points

The `scripts/` directory contains high-level entry-point scripts that
users are expected to run directly.

Typical uses include:
- reproducing paper results,
- running minimal example simulations,
- executing batch runs of predefined configuration sets.

Scripts in this directory should **orchestrate workflows**, not implement
core model logic.

---

## `paper/` — Manuscript-Related Materials

The `paper/` directory contains materials used during manuscript
preparation, such as:
- figure-to-script mapping notes,
- draft method text,
- reviewer response notes.

Nothing in this directory is required to run the model or generate
results.

---

## `supplemental/` — Paper Supplementary Materials

The `supplemental/` directory contains formal supplementary materials
referenced by the paper.

Examples include:
- detailed state-machine definitions,
- extended controller logic tables,
- parameter lists and bounds,
- sensitivity analyses.

Files in this directory are intended to be referenced explicitly in the
paper (e.g., Supplement S1, S2, etc.) and should remain stable after
submission.

---

## `tools/` — Auxiliary Utilities and Tooling

The `tools/` directory contains general-purpose utilities that support
development, inspection, or presentation, but do **not** affect
simulation behavior or experimental definition.

### Subdirectories

- **`inspection/`**  
  Tools for inspecting project structure or metadata, such as directory
  tree viewers.

- **`visualization/`**  
  Tools for plotting or visually exploring numerical data and timelines.

- **`formatting/`**  
  Tools for converting or packaging artifacts, such as combining scripts
  into PDFs or generating formatted documentation.

- **`misc/`**  
  Small or one-off utilities that do not yet warrant a dedicated
  category.

Tools are optional and should never be required to run the simulation.

---

## Top-Level Files

- **`README.md`**  
  High-level description of the project, its purpose, and instructions
  for reproducing results.

- **`.gitignore`**  
  Specifies which generated files and directories are excluded from
  version control.

---

## Design Philosophy Summary

This repository structure is designed to:
- separate scientific logic from tooling,
- ensure reproducibility of results,
- support publication and review,
- and allow long-term extension without structural refactoring.

When adding new files, consider the question:

> “Does this define what is being done, how it is implemented, support
> the paper, or help me work more efficiently?”

The answer determines the correct location.