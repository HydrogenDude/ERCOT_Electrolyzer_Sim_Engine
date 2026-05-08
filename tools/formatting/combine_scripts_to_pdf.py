import os
import sys
import tomllib
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

CONFIG_FILE = os.path.join(ROOT_DIR, "configs/script_groups.toml")
EXPORT_DIR = os.path.join(ROOT_DIR, "exports", "pdf")

PAGE_WIDTH, PAGE_HEIGHT = LETTER
LEFT_MARGIN = 0.75 * inch
TOP_MARGIN = PAGE_HEIGHT - 0.75 * inch
LINE_HEIGHT = 12

# ------------------------------------------------------------
# Load config
# ------------------------------------------------------------

def load_config():
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)

# ------------------------------------------------------------
# PDF helpers
# ------------------------------------------------------------

def new_page(c, title):
    c.showPage()
    c.setFont("Courier", 10)
    c.drawString(LEFT_MARGIN, TOP_MARGIN, title)
    return TOP_MARGIN - 2 * LINE_HEIGHT

def draw_line(c, text, y):
    if y < inch:
        y = new_page(c, "")
    c.drawString(LEFT_MARGIN, y, text)
    return y - LINE_HEIGHT

# ------------------------------------------------------------
# Combine to PDF
# ------------------------------------------------------------

def combine_group_to_pdf(group_name):
    config = load_config()

    if group_name not in config:
        raise KeyError(f"Group '{group_name}' not found")

    group = config[group_name]
    files = group.get("files", [])
    language = group.get("language", "unknown").upper()

    os.makedirs(EXPORT_DIR, exist_ok=True)
    output_pdf = os.path.join(EXPORT_DIR, f"{group_name}.pdf")

    c = canvas.Canvas(output_pdf, pagesize=LETTER)
    c.setFont("Courier", 10)

    y = TOP_MARGIN
    title = f"{group_name} ({language})"
    y = draw_line(c, title, y)
    y = draw_line(c, "=" * len(title), y - LINE_HEIGHT)

    for rel_path in files:
        abs_path = os.path.join(ROOT_DIR, rel_path)

        y = draw_line(c, "", y)
        y = draw_line(c, f"# FILE: {rel_path}", y)
        y = draw_line(c, "-" * 60, y)

        if not os.path.exists(abs_path):
            y = draw_line(c, f"[ERROR] File not found: {rel_path}", y)
            continue

        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                y = draw_line(c, line.rstrip("\n"), y)

    c.save()
    print(f"[SUCCESS] PDF written: {output_pdf}")

# ------------------------------------------------------------
# CLI entry
# ------------------------------------------------------------

if __name__ == "__main__":
    config = load_config()

    if len(sys.argv) > 1:
        groups = sys.argv[1:]
    else:
        groups = list(config.keys())

    for group in groups:
        combine_group_to_pdf(group)
