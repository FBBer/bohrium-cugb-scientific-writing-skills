"""Read the text and merged cells retained by the PDF parser."""
import re
from reader import cli, data, details, esc, paragraph, section, table
TITLE = "文献文档解析"
NUMBER = re.compile(r"[+\-−]?(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+\-]?\d+)?%?")

def physical_table(item):
    rows = item.get("rows", [])
    cells = item.get("row_cells", [])
    if not rows:
        return ""
    positions = [c for row in cells for c in row if c]
    xs = sorted({round(c[i], 2) for c in positions for i in (0, 2)})
    ys = sorted({round(c[i], 2) for c in positions for i in (1, 3)})
    covered = set()
    grid = []
    external = item.get("external_header", {}).get("names", [])
    headers = 0 if external else 1
    for ri, row in enumerate(rows):
        elements = []
        for ci, value in enumerate(row):
            if (ri,ci) in covered:
                continue
            rect = cells[ri][ci] if ri < len(cells) and ci < len(cells[ri]) else None
            right = down = 1
            if rect:
                right = max(1, sum(rect[0] + .1 < x <= rect[2] + .1 for x in xs))
                down = max(1, sum(rect[1] + .1 < y <= rect[3] + .1 for y in ys))
                for j in range(ri, min(ri+down, len(rows))):
                    for k in range(ci, min(ci+right, len(row))):
                        covered.add((j,k))
                if not external and ri == 0 and right > 1 and len(rows) > 1:
                    headers = 2
            spans = (f' colspan="{right}"' if right>1 else "") + (f' rowspan="{down}"' if down>1 else "")
            tag = "th" if ri < headers else "td"
            number = bool(NUMBER.fullmatch(str(value or "").strip())) or (value == 0 and value is not None)
            # Column alignment follows its actual numeric cells, even for a missing value.
            numeric_col = any(ci < len(r) and NUMBER.fullmatch(str(r[ci]).strip()) for r in rows[headers:])
            align = ' class="num"' if number or numeric_col and right==1 else ""
            scope = (' scope="colgroup"' if right>1 else ' scope="col"') if tag == "th" else ""
            elements.append(f'<{tag}{scope}{spans}{align}>' + esc(value) + f'</{tag}>')
        grid.append("<tr>" + "".join(elements) + "</tr>")
    head = "".join(grid[:headers])
    if external:
        labels = []
        for col, name in enumerate(external):
            numeric = any(col < len(r) and NUMBER.fullmatch(str(r[col]).strip()) for r in rows)
            align = ' class="num"' if numeric else ""
            labels.append(f'<th scope="col"{align}>' + esc(name) + '</th>')
        head = "<tr>" + "".join(labels) + "</tr>"
    original = '<div class="readtable"><table><thead>' + head + '</thead><tbody>' + "".join(grid[headers:]) + '</tbody></table></div>'
    values = []
    for band in item.get("aligned_measurements", []):
        names = [c.get("heading") or "第 "+str(c["column"])+" 列" for c in band["columns"]]
        values.append(table(["原表行名",*names], ([r["label"],*r["values"]] for r in band["records"]), range(1,len(names)+1)))
    return original + details("按原表行名读取数值", "".join(values))

def body(source):
    layout = data(source)
    chapters = []
    for page in layout.get("pages", []):
        tables = "".join(physical_table(t) for t in page.get("tables", []))
        lines = "".join(paragraph(r.get("display_text",r["text"])) for r in page.get("lines", []) if r.get("text"))
        if tables:
            lines = details("本页原文", lines)
        chapters.append(section("第 " + str(page["page"]) + " 页", tables + lines))
    return "".join(chapters) or paragraph("没有可显示的页面文本。")

if __name__ == "__main__":
    cli(TITLE, body)
