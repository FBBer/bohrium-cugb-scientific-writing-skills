"""Show citation renumbering beside the original sentence, then the bibliography."""
from reader import cli, data, details, manuscript, paragraph, section, table

TITLE = "引文与参考文献"

def body(source):
    report = data(source)
    occurrences = report.get("occurrences", [])
    rows = [(r.get("sentence", {}).get("text", ""), r.get("old"), r.get("new")) for r in occurrences]
    mapping = table(("原稿句子", "原编号", "新编号"), rows, numeric=(1, 2))
    works = [(r["number"], r["record"].get("title"), r["record"].get("DOI") or r["record"].get("id")) for r in report.get("cited", [])]
    text = source.with_name("manuscript.md")
    complete = details("修订全文", manuscript(text.read_text(encoding="utf-8"))) if text.is_file() else ""
    return mapping + section("文中引用的文献", table(("序号", "题名", "文献标识"), works, numeric=(0,))) + complete

if __name__ == "__main__":
    cli(TITLE, body)
