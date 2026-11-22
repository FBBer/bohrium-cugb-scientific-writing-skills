"""Publish a source-linked reading view using the same evidence as the notebook."""

from html import escape
import re

CSS = """
* {box-sizing:border-box}
body {margin:0;background:#fff;color:#000;font:19px/1.65 -apple-system,'PingFang SC','Segoe UI',sans-serif}
main {max-width:900px;margin:auto;padding:clamp(28px,5vw,66px) clamp(20px,5vw,50px)}
h1 {font-size:clamp(32px,4.2vw,48px);line-height:1.16;margin:0 0 32px}
h2 {font-size:clamp(25px,3vw,33px);margin:36px 0 12px}
h3 {font-size:22px;margin:30px 0 10px}
p {margin:8px 0 3px}
nav {display:flex;flex-wrap:wrap;gap:6px 24px}
article+article {margin-top:55px}
a,summary {color:inherit;text-underline-offset:.18em}
a:hover,summary:hover {background:#e9b85c}
:focus-visible {outline:2px solid currentColor;outline-offset:3px}
details {margin:2px 0 15px}
summary {cursor:pointer;width:fit-content}
blockquote {margin:8px 0 15px;overflow-wrap:anywhere}
mark {background:#e9b85c;color:#000}
.scroll {overflow-x:auto}
table {border-collapse:collapse;margin:10px 0;font-variant-numeric:tabular-nums}
td,th {text-align:left;vertical-align:top;padding:5px 24px 5px 0}
.role {font-weight:650}
"""


def compact(x):
    x = re.sub(r"\u00ad\s*\n\s*", "", x)
    x = re.sub(r"(?<=\w)-\s*\n\s*(?=[a-z])", "-", x)
    return " ".join(
        x.translate(
            str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"})
        ).split()
    )


def render(cards, tables, source_by_id, labels, en=False):
    esc = lambda x: escape(str(x))
    doc = [
        '<!doctype html><html lang="'
        + ("en" if en else "zh-CN")
        + '"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + ("Reading notes" if en else "阅读笔记")
        + "</title><style>"
        + CSS
        + "</style><main>"
    ]
    title = "Reading notes" if en else "阅读笔记"
    multiple = len(cards) != 1
    if multiple:
        doc.append(
            f"<h1>{title}</h1><nav>"
            + "".join(
                f'<a href="#paper-{i}">{esc(c["title"])}</a>'
                for i, c in enumerate(cards.values(), 1)
            )
            + "</nav>"
        )
    for i, (name, card) in enumerate(cards.items(), 1):
        level = 2 if multiple else 1
        doc.append(f'<article id="paper-{i}"><h{level}>{esc(card["title"])}</h{level}>')
        items = {x["anchor"]: x for x in card["notes"]}
        for chapter in card["outline"]:
            head = " › ".join(chapter["path"])
            if head:
                doc.append(f"<h{level+1}>{esc(head)}</h{level+1}>")
            for anchor in chapter["anchors"]:
                n = items[anchor]
                raw = source_by_id[n["id"]]["text"]
                a, b = n["start"], n["end"]
                if raw[a:b] != n["quote"]:
                    raise ValueError("Source quote mismatch: " + n["location"])
                label = labels[n["role"]]
                doc.append(
                    f'<p id="{esc(anchor)}"><span class="role">{esc(label)}</span>　{esc(compact(n["quote"]))}</p>'
                )
                where = f"{name} · {n['location']}"
                for key in n.get("conditions", []):
                    doc.append(
                        f'<a href="#{esc(key)}">'
                        + ("Scope" if en else "适用条件")
                        + "</a>"
                    )
                original = card["original_href"] + (
                    f"#page={n['page']}" if n.get("page") else ""
                )
                jump = (
                    f'<a href="{esc(original)}">'
                    + ("Open original" if en else "打开原文")
                    + "</a>"
                )
                doc.append(
                    "<details><summary>"
                    + ("Source" if en else "原文")
                    + "</summary><p>"
                    + esc(where) + "　"
                    + jump
                    + "</p><blockquote>"
                    + esc(raw[max(0, a - 75) : a])
                    + "<mark>"
                    + esc(raw[a:b])
                    + "</mark>"
                    + esc(raw[b : b + 75])
                    + "</blockquote></details>"
                )
        for file, t in tables.items():
            if t["paper"] != name:
                continue
            doc.append(
                "<h3>"
                + esc(file)
                + '</h3><div class="scroll"><table><thead><tr>'
                + "".join("<th>" + esc(x) + "</th>" for x in t["headers"])
                + "</tr></thead><tbody>"
            )
            for row in t["rows"][:12]:
                doc.append(
                    "<tr>"
                    + "".join("<td>" + esc(x) + "</td>" for x in row["values"])
                    + "</tr>"
                )
            doc.append("</tbody></table></div>")
            if len(t["rows"]) > 12:
                doc.append(
                    "<p>"
                    + ("Rows 1–12 of " if en else "显示前 12 行，共 ")
                    + str(len(t["rows"]))
                    + (" rows." if en else " 行。")
                    + "</p>"
                )
        doc.append("</article>")
    return "".join(doc) + "</main></html>\n"
