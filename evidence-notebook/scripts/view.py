"""Keep each reading note beside its original source locations."""
import re
from reader import cli, details, esc, paragraph, section, text_blocks

TITLE = "结构化阅读笔记"

def body(source):
    sections, paragraphs, references = [], [], []
    heading = ""
    def finish():
        content = '<div class="prose">' + "".join(paragraphs) + '</div>'
        sources = details("原文位置", "".join(paragraph(s) for s in dict.fromkeys(references)))
        return section(heading, content + sources) if heading else content + sources
    for block in text_blocks(source.read_text(encoding="utf-8")):
        title = re.fullmatch(r"#{1,6}\s+([^\n]+)", block)
        if title:
            if paragraphs:
                sections.append(finish())
            heading, paragraphs, references = title[1], [], []
        else:
            locations = re.findall(r"〔([^〕]+)〕", block)
            # A shared location can cover several sentences in one paragraph.
            if len(locations) == 1:
                references.extend(locations)
                block = block.replace("〔" + locations[0] + "〕", "").strip()
            paragraphs.append(paragraph(block))
    if paragraphs:
        sections.append(finish())
    return "".join(sections)

if __name__ == "__main__":
    cli(TITLE, body, "章节笔记", (("paper-cards.json", "论文卡片"), ("topic-index.json", "主题索引")))
