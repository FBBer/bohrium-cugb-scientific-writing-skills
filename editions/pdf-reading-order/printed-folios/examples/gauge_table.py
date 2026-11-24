"""Write a sample field table, including a blank cell, upper limit and footnote."""
from pathlib import Path
import sys
import pymupdf

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
with pymupdf.open() as doc:
    page = doc.new_page(width=510, height=380)
    page.insert_text((32, 32), "Water-level measurements", fontsize=12)
    page.insert_text((32, 62), "Table 1. Gauge comparison", fontsize=12)
    rows = [(88, ("Station", "Offset", "Travel time")), (103, ("", "(cm)", "(s)")),
            (125, ("Upstream", "1.2 ± 0.3", "4.0 ± 0.5")), (144, ("Midstream", "< 0.2", "")),
            (163, ("Downstream", "2.0 ± 0.1", "6.5 ± 0.4")), (183, ("Note: repeated readings.", "", ""))]
    for y, row in rows:
        for x, value in zip((34, 200, 340), row):
            if value:
                page.insert_text((x, y), value, fontsize=11)
    doc.save(path)
