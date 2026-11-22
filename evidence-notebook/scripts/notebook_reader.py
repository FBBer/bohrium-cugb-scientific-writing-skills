"""Publish a source-linked reading view using the same evidence as the notebook."""

from html import escape
import re

CSS = """*{box-sizing:border-box}body{margin:0;background:white;color:#000;font:18px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}main{max-width:1050px;margin:0 auto;padding:2.4rem clamp(1rem,4vw,3rem) 4rem}h1{font-size:clamp(1.9rem,4vw,2.8rem);line-height:1.16;margin:0 0 .7rem}h2{font-size:1.55rem;margin:1.8rem 0 .65rem}h3{font-size:1.18rem;margin:1.2rem 0 .2rem}a,summary{color:#000;text-underline-offset:.18em}a:hover,summary:hover{background:#e6b14d}nav{padding:.4rem 0 .9rem;border-bottom:2px solid #000;display:flex;flex-wrap:wrap;gap:.2rem 1.3rem}article+article{border-top:2px solid #000;margin-top:2rem;padding-top:1.3rem}p{margin:.3rem 0 .6rem}details{margin:.2rem 0 .8rem}summary{cursor:pointer}blockquote{border-left:3px solid #000;margin:.45rem 0;padding:.35rem .8rem;background:#fff}mark{background:#e7b04a;color:#000}table{border-collapse:collapse;max-width:100%;margin:.5rem 0}td,th{padding:.3rem .7rem;border-bottom:1px solid #000;text-align:left;vertical-align:top}th{border-bottom:2px solid #000}.scroll{overflow:auto}.role{font-weight:700}.meta{margin:.3rem 0;color:#000}"""


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
    doc.append(
        f"<h1>{title}</h1><nav>"
        + "".join(
            f'<a href="#paper-{i}">{esc(c["title"])}</a>'
            for i, c in enumerate(cards.values(), 1)
        )
        + "</nav>"
    )
    for i, (name, card) in enumerate(cards.items(), 1):
        doc.append(f'<article id="paper-{i}"><h2>{esc(card["title"])}</h2>')
        items = {x["anchor"]: x for x in card["notes"]}
        for chapter in card["outline"]:
            head = " › ".join(chapter["path"])
            if head:
                doc.append("<h3>" + esc(head) + "</h3>")
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
                    + esc(where)
                    + "</summary>"
                    + jump
                    + "<blockquote>"
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
