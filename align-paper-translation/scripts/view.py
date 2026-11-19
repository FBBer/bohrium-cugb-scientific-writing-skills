"""Show the submitted translation beside the matching source segment."""
import re
from reader import cli, data, details, esc, paragraph, parallels, text_blocks

TITLE = "文献翻译"

def body(source):
    text = source.read_text(encoding="utf-8")
    audit = source.with_name("audit.json")
    aligned = data(audit).get("alignment", []) if audit.is_file() else []
    rendered = "\n\n".join(f"### {r['id']} · {r['location']}\n\n{r['original']}\n\n{r['target']}" for r in aligned)
    if aligned and text.strip() == rendered.strip():
        groups = [(r["location"], [r["original"], r["target"]]) for r in aligned]
    else:
        groups = []
        for part in re.split(r"(?m)(?=^### )", text):
            if not part.strip():
                continue
            heading, _, content = part.partition("\n")
            if heading.startswith("### "):
                groups.append((heading[4:].partition(" · ")[2] or heading[4:], text_blocks(content)))
            else:
                groups.append(("", text_blocks(part)))
    rows, chunks, locations = [], [], []
    for loc, blocks in groups:
        if len(blocks) == 2:
            rows.append(tuple(paragraph(x) for x in blocks))
        else:
            chunks.extend([parallels("原文", "译文", rows), "".join(paragraph(x) for x in blocks)])
            rows = []
        if loc:
            locations.append(paragraph(loc))
    return "".join(chunks) + parallels("原文", "译文", rows) + details("段落位置", "".join(locations))

if __name__ == "__main__":
    cli(TITLE, body)
