from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ============================
# Configuration
# ============================

EXCLUDED_DIRS = {
    # Python
    "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build",
    ".git", ".idea", ".vscode",

    # MATLAB
    "slprj", "codegen", ".matlab", "resources",
}

EXCLUDED_FILES = {
    "__init__.py", ".DS_Store", "Thumbs.db"
}

EXCLUDED_SUFFIXES = {
    # Python
    ".pyc", ".pyo",

    # MATLAB
    ".asv", ".mexw64", ".mexa64",

    # Generic
    ".log", ".tmp", ".obj"
}

MATLAB_EXTS = {".m", ".mlx", ".mat", ".slx", ".prj"}
PYTHON_EXTS = {".py"}

# ============================
# Helpers
# ============================

def classify_path(path: Path) -> str:
    """Return a classification label for known MATLAB / Python structures."""
    name = path.name

    if path.is_dir():
        if name.startswith("+"):
            return " [MATLAB package]"
        if name.startswith("@"):
            return " [MATLAB class]"
        if name == "__pycache__":
            return " [Python cache]"
        if (path / "__init__.py").exists():
            return " [Python module]"
    else:
        if path.suffix in MATLAB_EXTS:
            return " [MATLAB]"
        if path.suffix in PYTHON_EXTS:
            return " [Python]"

    return ""

def is_visible(path: Path) -> bool:
    """Return True if this file/dir should appear in the tree."""
    if path.is_dir():
        return path.name not in EXCLUDED_DIRS
    if path.is_file():
        if path.name in EXCLUDED_FILES:
            return False
        if path.suffix in EXCLUDED_SUFFIXES:
            return False
    return True

# ============================
# Tree Printer
# ============================

def tree(path: Path, prefix: str = ""):
    items = [
        p for p in sorted(path.iterdir(), key=lambda p: p.name.lower())
        if is_visible(p)
    ]
    count = len(items)

    for idx, item in enumerate(items):
        connector = "└── " if idx == count - 1 else "├── "
        label = classify_path(item)
        print(prefix + connector + item.name + label)

        if item.is_dir():
            extension = "    " if idx == count - 1 else "│   "
            tree(item, prefix + extension)

# ============================
# Entry Point (with popup)
# ============================

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the empty Tk window

    selected_dir = filedialog.askdirectory(
        title="Select directory to generate tree",
        initialdir=Path.cwd()
    )

    if not selected_dir:
        print("No directory selected. Exiting.")
    else:
        root_path = Path(selected_dir)
        print(root_path.resolve())
        tree(root_path)
