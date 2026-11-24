"""Show each parsed passage, table and figure on the page where it was observed."""
import argparse
import base64
import hashlib
from html import escape
import os
from pathlib import Path
import re
import tempfile

from casework import read


def file_digest(path):
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for part in iter(lambda:handle.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def page_numbers(spec, size):
    if not spec:
        return list(range(1,size+1))
    result = set()
    for item in spec.split(","):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?",item.strip())
        if not match:
            raise ValueError("supply physical pages such as 1,3-5")
        start, end = int(match[1]),int(match[2] or match[1])
        if not 1 <= start <= end <= size:
            raise ValueError("page number outside the source PDF")
        result.update(range(start,end+1))
    return sorted(result)


def regions(page):
    for line in page["lines"] + page.get("marginalia", []):
        yield line["id"], line["bbox"], line.get("display_text", line["text"])
    for i,table in enumerate(page["tables"],1):
        if "bbox" not in table:
            continue
        yield f"p{page['page']}:t{i}", table["bbox"], f"表格 {i}"
        for row, cells in enumerate(table.get("text_cells") or table.get("row_cells", []), 1):
            values = table["rows"][row-1]
            for col, box in enumerate(cells, 1):
                if box and col <= len(values) and values[col-1]:
                    yield f"p{page['page']}:t{i}:r{row}:c{col}", box, f"表 {i} · {row} 行 {col} 列 · {values[col-1]}"
    for i,box in enumerate(page["images"],1):
        yield f"p{page['page']}:i{i}", box, f"图像 {i}"


def page_index(page, entries):
    anchors = {key for key, _, _ in entries}
    lines = page["lines"] + page.get("marginalia", [])
    table_ids, covered, tables = set(), set(), []
    clean = lambda value: " ".join(str(value or "").split())

    def link(key, label):
        return f'<a href="#{escape(key)}">{escape(str(label))}</a>'

    for number, table in enumerate(page["tables"], 1):
        key = f"p{page['page']}:t{number}"
        if key not in anchors or not table.get("rows"):
            continue
        table_ids.add(key)
        x0, y0, x1, y1 = table["bbox"]
        values = {clean(v) for row in table["rows"] for v in row if v}
        caption = table.get("caption") or f"表 {number}"
        notes = table.get("footnotes") or []
        for line in lines:
            ax, ay, bx, by = line["bbox"]
            text = clean(line.get("display_text", line["text"]))
            if text in values and x0-2 <= (ax+bx)/2 <= x1+2 and y0-2 <= (ay+by)/2 <= y1+2:
                covered.add(line["id"])
            if text == clean(caption) and abs(by-y0) < 45:
                covered.add(line["id"])
            if any(text == clean(n["text"]) and abs(ay-n["bbox"][1]) < 3 for n in notes):
                covered.add(line["id"])
        html = [f'<div class="table-wrap"><table><caption>{link(key, caption)}</caption><tbody>']
        for row, values in enumerate(table["rows"], 1):
            html.append("<tr>")
            for col, value in enumerate(values, 1):
                cell = f"{key}:r{row}:c{col}"
                table_ids.add(cell)
                label = str(value) if value is not None else ""
                if not label:
                    html.append('<td aria-label="原表留空"></td>')
                else:
                    html.append("<td>" + (link(cell, label) if cell in anchors else escape(label)) + "</td>")
            html.append("</tr>")
        html.append("</tbody></table>")
        html.extend(f'<p>{escape(n["text"])}</p>' for n in notes)
        tables.append("".join(html) + "</div>")
    other = [link(key, label) for key, _, label in entries if key not in table_ids and key not in covered]
    if other:
        tables.append("<ol>" + "".join(f"<li>{item}</li>" for item in other) + "</ol>")
    return '<div class="index">' + "".join(tables) + "</div>"


STYLE = """body{margin:0;font:17px/1.5 system-ui,sans-serif;color:#000;background:#fff}
main{max-width:1300px;margin:auto;padding:1rem 3vw}h1{font-size:1.65rem;overflow-wrap:anywhere}
.spread{display:grid;grid-template-columns:minmax(0,3fr) minmax(15rem,2fr);gap:2rem;align-items:start;margin-bottom:3rem}
svg{width:100%;height:auto;border:1px solid #000}.mark{fill:none;stroke:none}
.mark:target{fill:#ce8a20;fill-opacity:.40;stroke:#000;stroke-width:2;vector-effect:non-scaling-stroke}
.index{max-height:80vh;overflow:auto}.table-wrap{overflow-x:auto;margin:0 0 1.4rem}
table{border-collapse:collapse;width:max-content;max-width:100%}caption{text-align:left;font-weight:650;margin:0 0 .65rem}
td{padding:.35rem .8rem;border-bottom:1px solid #000;text-align:left}td:first-child{padding-left:0}
.table-wrap p{margin:.65rem 0 0}ol{padding-left:2rem;margin-top:0}li{margin:0 0 .45rem}
a{color:#000;text-underline-offset:.15em}a:hover,a:focus{background:#dba94e}
@media(max-width:700px){.spread{grid-template-columns:1fr;gap:1rem}.index{max-height:none}}"""


def export(pdf, layout, out, spec=None):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    if layout.get("source_sha256") != file_digest(pdf):
        raise ValueError("this layout does not identify the same PDF; parse the source file again")
    if out.resolve() == pdf.resolve() or out.suffix.lower() not in {".htm",".html"}:
        raise ValueError("choose an HTML output filename")
    out.parent.mkdir(parents=True, exist_ok=True)
    filename = None
    try:
        with fitz.open(pdf) as doc, tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=out.parent,delete=False) as stream:
            filename = stream.name
            pages = page_numbers(spec, len(doc))
            stream.write('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
            title = escape(pdf.name)
            stream.write(f"<title>{title}</title><style>{STYLE}</style><main><h1>{title}</h1>")
            for number in pages:
                record = layout["pages"][number-1]
                page = doc[number-1]
                if page.rotation:
                    page.set_rotation(0)
                width,height = record["size"]
                if record["page"] != number or max(abs(page.rect.width-width),abs(page.rect.height-height)) > 1:
                    raise ValueError(f"page geometry differs at page {number}")
                bitmap = page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).tobytes("png")
                encoded = base64.b64encode(bitmap).decode("ascii")
                stream.write(f'<section><h2>第 {number} 页</h2><div class="spread"><svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="第 {number} 页原文" viewBox="0 0 {width} {height}">')
                stream.write(f'<image width="{width}" height="{height}" href="data:image/png;base64,{encoded}"/>')
                entries = list(regions(record))
                for anchor,box,_ in entries:
                    x,y,right,bottom = box
                    stream.write(f'<rect class="mark" id="{escape(anchor)}" x="{x}" y="{y}" width="{max(0,right-x)}" height="{max(0,bottom-y)}"/>')
                stream.write("</svg>" + page_index(record, entries) + "</div></section>")
            stream.write("</main></html>\n")
        os.replace(filename,out)
    finally:
        if filename:
            Path(filename).unlink(missing_ok=True)
    return pages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf",type=Path)
    parser.add_argument("layout",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--pages")
    args = parser.parse_args()
    try:
        pages = export(args.pdf,read(args.layout),args.out,args.pages)
        print(len(pages),"source pages")
    except (ImportError,OSError,RuntimeError,ValueError) as exc:
        parser.exit(2,str(exc)+"\n")
