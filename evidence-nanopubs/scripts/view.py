"""Read published statements with their scope, provenance and quotations."""
from reader import cli, data, details, esc, paragraph, table

TITLE = "微出版断言"
QUALIFIERS = {"negative":"否定","uncertain":"不确定","inference":"推断","reported-by-others":"转述","hedged":"带限定的表述","tentative":"暂定"}

def body(source):
    rows = data(source)["claims"]
    if not rows:
        return paragraph("材料中没有可发布的断言。")
    statements = []
    for row in rows:
        evidence = "".join(paragraph(e.get("quote", "")) for e in row.get("evidence", []))
        qualifying = [QUALIFIERS.get(row[k], row[k]) for k in ("polarity", "evidence_type", "claim_strength")
                      if row.get(k) and row[k] not in {"positive", "direct", "asserted", "none"}]
        details_text = evidence + paragraph(row.get("reason"))
        if row.get("nanopub_id"):
            details_text += paragraph(row["nanopub_id"])
        scope = " · ".join([row["scope"], *dict.fromkeys(qualifying)])
        statements.append('<article class="piece"><h2>' + esc(scope) + '</h2>' +
                          paragraph(row["statement"], "lead") + details("断言出处", details_text) + '</article>')
    return "".join(statements)

if __name__ == "__main__":
    cli(TITLE, body)
