"""Generate a short, invented instrument table without printing any grid lines."""

from pathlib import Path
import sys

try:
    import pymupdf as fitz
except ImportError:
    import fitz

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
with fitz.open() as doc:
    page = doc.new_page(width=480, height=350)
    page.insert_text((40, 58), "Table 1. Readings at three stations.", fontsize=13)
    for ri, row in enumerate(
        [
            ("Station", "Offset (mV)", "Drift (mV)"),
            ("North", "4.2", "0.8"),
            ("South", "", "1.1"),
            ("East", "3.5", "0.9"),
        ]
    ):
        for x, value in zip((42, 195, 330), row):
            if value:
                page.insert_text((x, 85 + ri * 19), value, fontsize=11)
    page.insert_text(
        (42, 169), "Note: the southern offset was not measured.", fontsize=10
    )
    doc.save(path)
