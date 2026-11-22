"""Render the paper, its findings and its original evidence as an offline reading page."""

from html import escape
from pathlib import Path
import re

CSS = """
* {box-sizing:border-box}
html {background:#fff;color:#000}
body {margin:0;font:19px/1.52 -apple-system,'PingFang SC','Segoe UI',sans-serif}
main {max-width:1000px;margin:auto;padding:clamp(22px,4vw,48px) clamp(19px,4vw,44px)}
h1,h2,h3 {line-height:1.24}
h1 {font-size:clamp(32px,4vw,45px);margin:22px 0}
h2 {font-size:clamp(24px,2.8vw,31px);margin:27px 0 12px}
h3 {font-size:22px;margin:24px 0 10px}
p {margin:9px 0 3px}
nav,.folio,footer {display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 23px}
.folio {justify-content:space-between;border-bottom:2px solid #000;padding-bottom:9px;overflow-wrap:anywhere}
footer {border-top:1px solid #000;margin:30px 0 8px;padding-top:12px}
article+article {margin-top:52px}
a,summary {color:#000;text-underline-offset:.16em}
a:focus-visible,summary:focus-visible {outline:2px solid #000;outline-offset:3px}
a:hover,summary:hover {background:#e8b24f}
details {margin:3px 0 14px}
summary {width:fit-content;cursor:pointer}
blockquote {border-left:3px solid #000;margin:8px 0 16px;padding:2px 0 2px 14px;overflow-wrap:anywhere}
mark,.passage:target {background:#efc36d;color:#000}
.scroll {overflow-x:auto}
table {border-collapse:collapse;width:100%;margin:4px 0 12px;text-align:left;font-variant-numeric:tabular-nums}
th,td {padding:7px 17px 7px 0;vertical-align:top;overflow-wrap:anywhere}
thead {border-bottom:1.5px solid #000}
tbody tr+tr {border-top:1px solid #000}
td:last-child,th:last-child {padding-right:0}
.passage {scroll-margin-top:18px}
ul {margin:4px 0 14px;padding-left:24px}
@media(max-width:600px){body{font-size:18px}th,td{padding-right:10px}.scroll table{min-width:365px}}
@media print {body{font-size:11pt}main{max-width:none;padding:0}.scroll{overflow:visible}
thead{display:table-header-group}tr,blockquote,footer{break-inside:avoid}h1,h2,h3{break-after:avoid}}
"""


def compact(x):
    x = re.sub(r"\u00ad\s*\n\s*", "", x)
    x = re.sub(r"(?<=\w)-\s*\n\s*(?=[a-z])", "-", x)
    return " ".join(
        x.translate(
            str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"})
        ).split()
    )


def passage_groups(anchors, items, sources):
    """Only rejoin adjacent sentences already present in the same original paragraph."""
    group = []
    for anchor in anchors:
        note = items[anchor]
        raw = sources[note["id"]]["text"]
        if raw[note["start"] : note["end"]] != note["quote"]:
            raise ValueError("Source quote mismatch: " + note["location"])
        if group:
            previous = group[-1]
            if (
                previous["id"] != note["id"]
                or previous["end"] > note["start"]
                or raw[previous["end"] : note["start"]].strip()
            ):
                yield group
                group = []
        group.append(note)
    if group:
        yield group


def join_passage(group, raw, fmt):
    pieces = []
    for i, note in enumerate(group):
        if i and raw[group[i - 1]["end"] : note["start"]]:
            pieces.append(" ")
        pieces.append(fmt(note))
    return "".join(pieces)


def display_location(location, en):
    lines = re.fullmatch(r"L(\d+)-(\d+)", location)
    if lines:
        start, end = lines.groups()
        if start == end:
            return f"Line {start}" if en else f"原文第 {start} 行"
        return f"Lines {start}–{end}" if en else f"原文第 {start}–{end} 行"
    block = re.fullmatch(r"p(\d+):B(\d+)", location)
    if block:
        page, n = block.groups()
        return f"Page {page}, block {n}" if en else f"原文第 {page} 页 · 第 {n} 块"
    return ("Source · " if en else "原文 · ") + location


def issue_label(reason, en):
    if reason.startswith("no text layer"):
        return "No extractable text on this page" if en else "此页没有可提取的文字"
    if reason == "encrypted PDF":
        return "Encrypted PDF" if en else "PDF 已加密"
    if reason == "no eligible prose passages":
        return "No passages available for notes" if en else "没有可摘录的正文段落"
    return reason


def link(href, text):
    return f'<a href="{escape(href, quote=True)}">{escape(text)}</a>'


def table(headings, rows):
    heading = "".join(f'<th scope="col">{escape(text)}</th>' for text in headings)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>'


def render(cards, tables, source_by_id, labels=None, en=False):
    def label(zh, english):
        return english if en else zh

    title = label("阅读笔记", "Reading notes")
    parts = [
        f'<!doctype html><html lang="{("en" if en else "zh-CN")}"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{escape(title)}</title><style>{CSS}</style></head><body><main>",
    ]
    many = len(cards) != 1
    if many:
        parts.extend(
            [
                f"<h1>{title}</h1><nav>",
                *(
                    link(f"#paper-{i}", c["title"])
                    for i, c in enumerate(cards.values(), 1)
                ),
                "</nav>",
            ]
        )
    for i, (name, card) in enumerate(cards.items(), 1):
        level = 2 if many else 1
        section = f"h{level + 1}"
        filename = Path(name).name
        parts.extend(
            [
                f'<article id="paper-{i}"><div class="folio"><b>{title}</b>',
                link(card["original_href"], name),
                "</div>",
                f"<h{level}>{escape(card['title'])}</h{level}>",
            ]
        )
        items = {n["anchor"]: n for n in card["notes"]}
        paired = [n for n in card["notes"] if n.get("conditions")]
        if paired:
            parts.append(
                f"<{section}>"
                + label("结果对照", "Results by section")
                + f"</{section}>"
            )
            rows = []
            for n in paired:
                scope = [items[key] for key in n["conditions"]]
                rows.append(
                    [
                        escape(" › ".join(n["path"])),
                        link("#" + n["anchor"], compact(n["quote"])),
                        "<br>".join(
                            link("#" + q["anchor"], compact(q["quote"])) for q in scope
                        ),
                    ]
                )
            parts.append(
                table(
                    [
                        label("章节", "Section"),
                        label("结果", "Finding"),
                        label("适用条件", "Scope"),
                    ],
                    rows,
                )
            )

        if card["source_issues"]:
            parts.append(
                f"<{section}>"
                + label("需查阅的原文", "Pages to consult")
                + f"</{section}><ul>"
            )
            for issue in card["source_issues"]:
                loc = issue.get("location", "")
                page = re.fullmatch(r"p(\d+)", loc)
                href = card["original_href"] + ("#page=" + page[1] if page else "")
                where = filename + (" · " + loc if loc else "")
                parts.append(
                    "<li>"
                    + link(href, where)
                    + "　"
                    + escape(issue_label(issue["reason"], en))
                    + "</li>"
                )
            parts.append("</ul>")

        for chapter in card["outline"]:
            heading = " › ".join(chapter["path"])
            if heading:
                parts.append(f"<{section}>{escape(heading)}</{section}>")
            for group in passage_groups(chapter["anchors"], items, source_by_id):
                first, last = group[0], group[-1]
                raw = source_by_id[first["id"]]["text"]

                def marked_note(note):
                    return f'<span id="{escape(note["anchor"])}" class="passage">{escape(compact(note["quote"]))}</span>'

                parts.append("<p>" + join_passage(group, raw, marked_note) + "</p>")
                original = card["original_href"] + (
                    f"#page={first['page']}" if first.get("page") else ""
                )
                start, end = first["start"], last["end"]
                parts.extend(
                    [
                        "<details><summary>"
                        + escape(display_location(first["location"], en))
                        + "</summary>",
                        link(original, label("打开原文", "Open original")),
                        "<blockquote>"
                        + escape(raw[max(0, start - 75) : start])
                        + "<mark>"
                        + escape(raw[start:end])
                        + "</mark>"
                        + escape(raw[end : end + 75])
                        + "</blockquote></details>",
                    ]
                )

        for file in card["table_files"]:
            t = tables[file]
            parts.append(
                f"<{section}>" + link(t["original_href"], file) + f"</{section}>"
            )
            rows = []
            for row in t["rows"][:12]:
                values = row["values"]
                cells = [str(row["row"])]
                for k in range(len(t["headers"])):
                    if k >= len(values):
                        cells.append(label("行中缺列", "Cell absent"))
                    elif not values[k].strip():
                        cells.append(label("原表留空", "Blank"))
                    else:
                        cells.append(escape(values[k]))
                rows.append(cells)
            parts.append(table([label("原表行", "Row"), *t["headers"]], rows))
            if len(t["rows"]) > 12:
                text = (
                    f"显示前 12 行，共 {len(t['rows'])} 行。"
                    if not en
                    else f"First 12 of {len(t['rows'])} rows."
                )
                parts.append("<p>" + text + "</p>")
        parts.extend(
            [
                "<footer><b>" + label("本篇文件", "Files") + "</b>",
                link(card["original_href"], label("论文原文", "Original paper")),
                link("notes.md", label("章节笔记", "Chapter notes")),
                link("study-matrix.tsv", label("论文对照表", "Study matrix")),
                "</footer></article>",
            ]
        )
    return "".join(parts) + "</main></body></html>\n"
