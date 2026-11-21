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
        yield f"p{page['page']}:t{i}", table["bbox"], f"表格 {i}"
    for i,box in enumerate(page["images"],1):
        yield f"p{page['page']}:i{i}", box, f"图像 {i}"


STYLE = """body{margin:0;font:17px/1.5 system-ui,sans-serif;color:#000;background:#fff}
main{max-width:1300px;margin:auto;padding:1rem 3vw}h1{font-size:1.65rem;overflow-wrap:anywhere}
.spread{display:grid;grid-template-columns:minmax(0,3fr) minmax(15rem,2fr);gap:2rem;align-items:start;margin-bottom:3rem}
svg{width:100%;height:auto;border:1px solid #777}.mark{fill:none;stroke:none}
.mark:target{fill:#f2c446;fill-opacity:.26;stroke:#000;stroke-width:2;vector-effect:non-scaling-stroke}
ol{padding-left:2rem;margin-top:0;max-height:80vh;overflow:auto}li{margin:0 0 .45rem}
a{color:#000;text-underline-offset:.15em}a:hover,a:focus{background:#f6dc85}
@media(max-width:700px){.spread{grid-template-columns:1fr;gap:1rem}ol{max-height:45vh}}"""


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
                stream.write("</svg><ol>")
                for anchor,_,label in entries:
                    stream.write(f'<li><a href="#{escape(anchor)}">{escape(label)}</a></li>')
                stream.write("</ol></div></section>")
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
