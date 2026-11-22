"""Offline reading pages. All source material is escaped before insertion."""
import argparse
import base64
from html import escape
import json
from pathlib import Path
import os
import re
from urllib.parse import quote

from casework import atomic_text

STYLE = """
:root{color-scheme:light;--ink:#000;--paper:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"Helvetica Neue","PingFang SC","Microsoft YaHei",Arial,sans-serif;font-size:19px;line-height:1.55}
main{max-width:1120px;margin:auto;padding:clamp(28px,5vw,66px);padding-bottom:75px}
h1,h2,h3,p,figure,dl,dd,blockquote{margin:0}
h1{font-size:clamp(32px,4.4vw,54px);font-weight:650;line-height:1.14;letter-spacing:-.045em;margin:0 0 44px}
h2{font-size:clamp(24px,3vw,32px);font-weight:630;line-height:1.24;letter-spacing:-.025em}
h3,summary,.colhead{font-size:18px;font-weight:650;line-height:1.45}
h2+p,h3+p{margin-top:12px}
p+p{margin-top:.8em}
article+article,.piece+.piece{margin-top:38px}
section+section{margin-top:40px}
section>h2,section>h3{margin-bottom:16px}
.prose{max-width:76ch;overflow-wrap:anywhere}
.prose p+h2{margin-top:34px}.prose+h2,.prose+details{margin-top:27px}
.piece h2+.lead{margin-top:14px}
.lead,.quotation{font-family:Georgia,"Songti SC","STSong",serif;font-weight:400;font-size:clamp(24px,2.8vw,35px);line-height:1.42;letter-spacing:-.013em;overflow-wrap:anywhere}
.prose p,.parallel p,td,th,pre{overflow-wrap:anywhere}
.parallel{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:clamp(28px,4vw,64px)}
.parallel>*,.spread>*{min-width:0}
.parallel p{font-size:clamp(19px,2.1vw,24px);line-height:1.55}
.pairrow{padding:17px 0}
.pairrow:last-child{padding-bottom:0}
.pairhead{padding-bottom:9px}
.change{font-weight:650;text-decoration:underline;text-decoration-thickness:1.5px;text-underline-offset:.15em}
.readtable{max-width:100%;overflow-x:auto}
table{width:100%;border-collapse:collapse;text-align:left;font-size:18px;line-height:1.43;font-variant-numeric:tabular-nums}
th,td{vertical-align:top;padding:12px 16px 12px 0;border:0}
th:last-child,td:last-child{padding-right:0}
thead th{font-weight:650}
.num{text-align:right;font-variant-numeric:tabular-nums}
pre{margin:0;white-space:pre-wrap;font:17px/1.55 "SFMono-Regular",Consolas,monospace;tab-size:4}
a{color:#000;text-underline-offset:.2em}
a:focus-visible,summary:focus-visible{outline:2px solid #000;outline-offset:4px}
details{margin-top:22px}summary{cursor:pointer;width:fit-content}details[open]>summary{margin-bottom:12px}
.source{margin:.65em 0;max-width:76ch}.source cite{font-style:normal;font-weight:600}
img{display:block;height:auto;max-width:100%}
.spread{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(24px,4vw,58px);align-items:start}
.spread h3{margin-bottom:12px}
.item+.item{margin-top:18px}
.drawing{overflow-x:auto}.drawing img{width:100%;min-width:540px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:20px;margin-top:24px}
.facts dt{font-size:17px}.facts dd{font-size:clamp(28px,3.5vw,42px);font-weight:580;line-height:1.25;font-variant-numeric:tabular-nums}
@media(max-width:650px){
 main{padding:27px 21px 44px}h1{margin-bottom:30px}.spread,.parallel{grid-template-columns:1fr;gap:12px}.pairhead{display:none}
 .pairrow [data-label]::before{content:attr(data-label);display:block;font:600 16px/1.5 "PingFang SC",sans-serif;margin-bottom:4px}
 table{font-size:16px}th,td{padding:9px 10px 9px 0}.readtable>table{min-width:min(445px,110vw)}
 .drawing img{min-width:530px}.facts{grid-template-columns:repeat(auto-fit,minmax(100px,1fr))}
}
@media print{main{max-width:none;padding:0}body{font-size:11pt}h1{font-size:23pt;margin-bottom:18pt}h2{font-size:16pt}
 .readtable,.drawing{overflow:visible}tr,figure,.pairrow{break-inside:avoid}.drawing img{min-width:0}h1,h2,h3{break-after:avoid}thead{display:table-header-group}}
"""

def esc(value):
    return escape(str(value)) if value is not None else ""

def data(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def paragraph(value, style=""):
    return '<p class="' + style + '">' + esc(value) + '</p>' if value else ""

def section(heading, content):
    return '<section><h2>' + esc(heading) + '</h2>' + content + '</section>' if content else ""

def details(heading, content):
    return '<details><summary>' + esc(heading) + '</summary>' + content + '</details>' if content else ""

def table(head, rows, numeric=()):
    rows = list(rows)
    if not rows:
        return ""
    def row(values, tag):
        cells = []
        for i, value in enumerate(values):
            cls = ' class="num"' if i in numeric else ""
            scope = ' scope="col"' if tag == "th" else ""
            cells.append(f'<{tag}{scope}{cls}>{esc(value)}</{tag}>')
        return "<tr>" + "".join(cells) + "</tr>"
    return '<div class="readtable"><table><thead>' + row(head, "th") + '</thead><tbody>' + "".join(row(r, "td") for r in rows) + '</tbody></table></div>'

def parallels(left, right, rows):
    header = '<div class="parallel pairhead"><span class="colhead">' + esc(left) + '</span><span class="colhead">' + esc(right) + '</span></div>'
    pairs = ['<div class="parallel pairrow"><div data-label="' + esc(left) + '">' + a + '</div><div data-label="' + esc(right) + '">' + b + '</div></div>' for a, b in rows]
    return header + "".join(pairs) if pairs else ""

def text_blocks(text):
    """Read the simple headings and paragraph blocks emitted by the writing tools."""
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

def manuscript(text):
    out = []
    for block in text_blocks(text):
        title = re.fullmatch(r'#{1,6}\s+([^\n]+)', block)
        if title:
            out.append('<h2>' + esc(title[1]) + '</h2>')
        else:
            out.append(paragraph(block))
    return '<article class="prose">' + "".join(out) + '</article>' if out else ""

def bitmap(raw, kind, alt):
    url = "data:" + kind + ";base64," + base64.b64encode(raw).decode("ascii")
    return '<img src="' + url + '" alt="' + esc(alt) + '">'

def document(title, content):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>' + esc(title) + '</title><style>' + STYLE + '</style></head><body><main><h1>' +
            esc(title) + '</h1>' + content + '</main></body></html>')

def cli(title, body, link_label=None):
    parser = argparse.ArgumentParser(description="用本地成果生成阅读页。")
    parser.add_argument("source", type=Path, help="本题的主成果文件")
    parser.add_argument("output", type=Path, help="阅读页的 HTML 文件名")
    args = parser.parse_args()
    if args.output.suffix.lower() not in {".htm", ".html"} or args.source.resolve() == args.output.resolve():
        parser.error("请选择单独的 HTML 输出文件。")
    content = body(args.source)
    if link_label:
        relative = os.path.relpath(args.source.resolve(), args.output.resolve().parent)
        content += '<p><a href="' + quote(Path(relative).as_posix(), safe="/") + '">' + esc(link_label) + '</a></p>'
    atomic_text(args.output, document(title, content))
