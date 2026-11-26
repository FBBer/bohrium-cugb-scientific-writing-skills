"""Locate a section starting across both columns even when its title is very short."""
import statistics

def section_breaks(lines, width, tables):
    text_sizes = [s["size"] for row in lines if row.get("role") == "body" for s in row.get("spans", [])]
    if not text_sizes:
        return []
    body_size = statistics.median(text_sizes)
    left = [r for r in lines if r.get("role") == "body" and r["bbox"][2] < width*.55]
    right = [r for r in lines if r.get("role") == "body" and r["bbox"][0] > width*.48]
    cuts = []
    for row in lines:
        x0, y0, x1, y1 = row["bbox"]
        if row.get("role") not in ("heading", "heading_candidate") or x0 > width*.28 or x1 > width*.49:
            continue
        if max((s["size"] for s in row.get("spans", [])), default=0) < body_size*1.16:
            continue
        if any(a <= x0 <= c and b <= y0 <= d for t in tables if "bbox" in t for a,b,c,d in [t["bbox"]]):
            continue
        # A heading in one column must never reorder text printed alongside it.
        clearance = body_size*.85
        if any(r["bbox"][3] > y0-clearance and r["bbox"][1] < y1+clearance for r in right):
            continue
        if all(sum(r["bbox"][3] <= y0 for r in col) >= 2 and
               sum(r["bbox"][1] >= y1 for r in col) >= 2 for col in (left,right)):
            cuts.append(row)
    return sorted(cuts,key=lambda r:r["bbox"][1])
