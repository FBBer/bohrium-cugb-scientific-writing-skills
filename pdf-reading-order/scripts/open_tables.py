"""Recover captioned tables without ruling lines from physical text positions."""

import csv
import io
import re
from statistics import median

CAPTION = re.compile(
    r"^\s*(?:table|tab\.|表)\s*(?:[a-z]?\d+[a-z]?|[ivxl]+|[一二三四五六七八九十]+)(?=\W|$)",
    re.I,
)
NOTE = re.compile(r"^\s*(?:notes?\s*[:.]|注[：:]|[*†‡]\s*\w|source\s*:)", re.I)
VALUE = re.compile(
    r"^(?:[<>≤≥~≈]?\s*[+−–-]?(?:\d+(?:[.,]\d+)*|\.\d+)|[—–-]$|n/?a$|nd$)", re.I
)


def bounds(parts):
    return [
        min(p[0] for p in parts),
        min(p[1] for p in parts),
        max(p[2] for p in parts),
        max(p[3] for p in parts),
    ]


def line_cells(words):
    """Keep spaces inside a label and split at gutters wider than ordinary word spaces."""
    groups = []
    for word in sorted(words, key=lambda w: w[0]):
        gap = max(9, 0.85 * (word[3] - word[1]))
        if not groups or word[0] - groups[-1][-1][2] > gap:
            groups.append([])
        groups[-1].append(word)
    return [(" ".join(w[4] for w in g), bounds(g)) for g in groups]


def text_rows(words):
    rows = []
    for w in sorted(words, key=lambda x: ((x[1] + x[3]) / 2, x[0])):
        if not w[4].strip():
            continue
        mid = (w[1] + w[3]) / 2
        if not rows or abs(mid - rows[-1][0]) > max(2, 0.32 * (w[3] - w[1])):
            rows.append((mid, []))
        rows[-1][1].append(w)
    return [(mid, line_cells(group)) for mid, group in rows]


def project(cells, cuts):
    slots = [("", None) for _ in range(len(cuts) + 1)]
    for text, box in cells:
        if any(box[0] + 1 < cut < box[2] - 1 for cut in cuts):
            return None
        col = sum((box[0] + box[2]) / 2 >= cut for cut in cuts)
        if slots[col][1] is not None:
            return None
        slots[col] = (text, box)
    return slots


def borderless(words, known):
    """A caption, aligned headings, recurring numeric rows and open gutters are required."""
    rows = text_rows(words)
    tables = []
    for pos, (mid, caption) in enumerate(rows):
        caption_text = " ".join(c[0] for c in caption)
        if not CAPTION.match(caption_text) or pos + 3 >= len(rows):
            continue
        hy, header = rows[pos + 1]
        height = median(c[1][3] - c[1][1] for c in header)
        n = len(header)
        if not 2 <= n <= 16 or hy - mid > max(38, 3.2 * height):
            continue
        if any(not re.search(r"[^\W\d_]", text) for text, _ in header):
            continue
        body = []
        notes = []
        previous_y = hy
        for y, cells in rows[pos + 2 :]:
            printed = " ".join(c[0] for c in cells)
            if y - previous_y > max(27, 2.15 * height) or CAPTION.match(printed):
                break
            if NOTE.match(printed):
                notes.append({"text": printed, "bbox": bounds([c[1] for c in cells])})
                previous_y = y
                continue
            if (
                notes
                or not 2 <= len(cells) <= n
                or not any(VALUE.match(t) for t, _ in cells[1:])
            ):
                break
            body.append(cells)
            previous_y = y
        complete = [row for row in body if len(row) == n]
        if len(body) < 2 or not complete:
            continue
        full = [header, *complete]
        cuts = []
        for col in range(n - 1):
            left = max(row[col][1][2] for row in full)
            right = min(row[col + 1][1][0] for row in full)
            if right - left < max(4, 0.4 * height):
                break
            cuts.append((left + right) / 2)
        if len(cuts) != n - 1:
            continue
        mapped = [project(row, cuts) for row in body]
        if any(row is None or row[0][1] is None for row in mapped):
            continue
        grid = [header, *mapped]
        boxes = [[cell[1] for cell in row] for row in grid]
        box = bounds([b for row in boxes for b in row if b])
        center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        overlaps = [
            t
            for t in known + tables
            if "bbox" in t
            and t["bbox"][0] - 2 <= center[0] <= t["bbox"][2] + 2
            and t["bbox"][1] - 2 <= center[1] <= t["bbox"][3] + 2
        ]
        if overlaps:
            # The library can detect an open table while omitting its caption and notes.
            # Add them only when the printed values agree column for column.
            for table in overlaps:
                observed = [
                    [str(value or "").strip() for value in row]
                    for row in table.get("rows", [])
                ]
                printed = [[text.strip() for text, _ in row] for row in grid]
                if observed == printed:
                    table["caption"] = caption_text
                    table["footnotes"] = notes
                    table["text_cells"] = boxes
            continue
        tables.append(
            {
                "bbox": box,
                "rows": [[text if b else None for text, b in row] for row in grid],
                "row_cells": boxes,
                "cells": [b for row in boxes for b in row if b],
                "method": "caption and aligned text",
                "caption": caption_text,
                "footnotes": notes,
            }
        )
    return tables


def table_tsv(pages):
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(
        (
            "page",
            "table",
            "row",
            "column",
            "row_label",
            "heading",
            "value",
            "bbox",
            "footnotes",
        )
    )
    for page in pages:
        for number, table in enumerate(page["tables"], 1):
            rows = table.get("rows", [])
            if not rows:
                continue
            external = table.get("external_header") or {}
            headings = external.get("names") or rows[0]
            start = 0 if external else 1
            positions = table.get("text_cells") or table.get("row_cells", [])
            columns = [
                c - 1 for c in table.get("reading_columns", range(1, len(headings) + 1))
            ]
            foot = " | ".join(x["text"] for x in table.get("footnotes", []))
            for r in range(start, len(rows)):
                values = rows[r]
                label = (
                    values[columns[0]] if columns and columns[0] < len(values) else ""
                )
                for col in columns:
                    box = (
                        positions[r][col]
                        if r < len(positions) and col < len(positions[r])
                        else None
                    )
                    writer.writerow(
                        (
                            page["page"],
                            number,
                            r + 1,
                            col + 1,
                            label,
                            headings[col] if col < len(headings) else "",
                            values[col] if col < len(values) else "",
                            ",".join(f"{v:.2f}" for v in box) if box else "",
                            foot,
                        )
                    )
    return out.getvalue()


def find_cell(layout, row_label, heading, page=None, table=None):
    import unicodedata

    def key(value):
        return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()

    cells = []
    for item in csv.DictReader(io.StringIO(table_tsv(layout["pages"])), delimiter="\t"):
        p, t = int(item["page"]), int(item["table"])
        if (page is not None and p != page) or (table is not None and t != table):
            continue
        if key(row_label) != key(item["row_label"]) or key(heading) != key(
            item["heading"]
        ):
            continue
        boxes = [float(x) for x in item["bbox"].split(",")] if item["bbox"] else None
        cells.append(
            {
                "page": p,
                "table": t,
                "row": int(item["row"]),
                "column": int(item["column"]),
                "row_label": item["row_label"],
                "heading": item["heading"],
                "printed": item["value"],
                "bbox": boxes,
                "footnotes": item["footnotes"],
                "anchor": f"p{p}:t{t}:r{item['row']}:c{item['column']}"
                if boxes
                else None,
            }
        )
    state = (
        "not_found"
        if not cells
        else "ambiguous"
        if len(cells) > 1
        else "value"
        if cells[0]["printed"]
        else "blank"
    )
    return {
        "file": layout.get("file"),
        "sha256": layout.get("source_sha256"),
        "state": state,
        "cells": cells,
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Locate a printed table value by exact row label and column heading."
    )
    parser.add_argument("layout", type=Path)
    parser.add_argument("--row", required=True)
    parser.add_argument("--column", required=True)
    parser.add_argument("--page", type=int)
    parser.add_argument("--table", type=int)
    args = parser.parse_args()
    answer = find_cell(
        json.loads(args.layout.read_text(encoding="utf-8")),
        args.row,
        args.column,
        args.page,
        args.table,
    )
    print(json.dumps(answer, ensure_ascii=False, indent=2))
    raise SystemExit(0 if answer["state"] in {"value", "blank"} else 1)
