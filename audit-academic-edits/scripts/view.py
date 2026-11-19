"""Show the revised manuscript and the exact changed passages."""
from reader import cli, data, details, esc, manuscript, parallels, paragraph

TITLE = "学术语言润色"

def marked(value, edits, key):
    cursor = 0
    spans = []
    for edit in edits:
        first, last = edit[key]
        if not cursor <= first <= last <= len(value):
            return paragraph(value)
        spans.append(esc(value[cursor:first]))
        if first < last:
            spans.append('<span class="change">' + esc(value[first:last]) + '</span>')
        cursor = last
    return '<p>' + "".join(spans) + esc(value[cursor:]) + '</p>'

def body(source):
    text = source.read_text(encoding="utf-8")
    prose = manuscript(text)
    report = source.with_name("audit.json")
    changes = data(report).get("changes", []) if report.is_file() else []
    if not changes or any(r["revised"] not in text for r in changes):
        return prose
    rows = [(marked(x["original"], x["edits"], "source_offsets"), marked(x["revised"], x["edits"], "target_offsets")) for x in changes]
    reasons = "".join(paragraph(" · ".join(str(v) for v in (x.get("location"), x.get("reason")) if v)) for x in changes)
    return parallels("原句", "修订稿", rows) + details("修改理由", reasons) + details("阅读全文", prose)

if __name__ == "__main__":
    cli(TITLE, body)
