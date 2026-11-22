"""Read sections in source order and retain physical locations for text evidence."""

from collections import defaultdict
import re
import unicodedata
from xml.etree import ElementTree as ET
from zipfile import ZipFile

WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NUMBER = re.compile(r"^(?P<number>\d+(?:\.\d+)*)(?:[.、)）])?\s+(?P<title>\S.{0,115})$")
CN_NUMBER = re.compile(
    r"^(?:第([一二三四五六七八九十\d]+)[章节]|[一二三四五六七八九十]+[、．])\s*(\S.{0,90})$"
)
APPENDIX = re.compile(
    r"^(?:appendix(?:\s+[A-Z](?=[.:\s]|$))?|supplement(?:ary material)?|附录(?:[A-Z一二三四五六\d])?)[.:：\s]*(.*)$",
    re.I,
)
STANDALONE = {
    "references": r"references(?: and notes)?|bibliography|acknowledg(?:e)?ments?|参考文献|引用文献|致谢",
    "abstract": r"abstract|summary|摘要|概要",
    "question": r"research questions?|objectives?|研究问题|研究目的",
    "method": r"materials?(?: and methods?)?|methods?|methodology|data(?:set)?s?|experimental (?:setup|design)|protocol|材料与方法|研究方法|观测安排|实验设置|研究设计|方法|数据",
    "finding": r"results?(?: and discussion)?|findings?|observations?|研究结果|主要发现|结果(?:与讨论)?|分区结果|实验结果",
    "interpretation": r"discussion|interpretation|conclusions?|讨论|结论|作者解释",
    "limitation": r"limitations?(?: and future work)?|scope|limitations? of (?:this|the) study|研究局限|局限(?:性)?|适用范围|限制",
    "context": r"introduction|background|related work|引言|绪论|背景|相关工作",
}
WORD_TEST = re.compile(r"[A-Za-z]{3}|[\u3400-\u9fff]")


def folded(text):
    text = re.sub(r"(?<=[a-z])[-\u00ad]\s*\n\s*(?=[a-z])", "", text)
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def heading_info(raw, style=None):
    line = " ".join(raw.strip().split())
    if style == 0 and 0 < len(line) <= 270:
        return 0, line, "section"
    if not line or len(line) > 125:
        return None
    level = style
    marked = re.fullmatch(r"(#{1,6})\s+(.+?)\s*#*", line)
    latex = re.fullmatch(r"\\((?:sub){0,2}section|chapter)\*?\{([^{}]+)\}", line)
    if marked:
        level, line = len(marked[1]), marked[2]
    elif latex:
        level, line = 1 + latex[1].count("sub"), latex[2]
    if not line:
        return None
    enumerated = NUMBER.fullmatch(line)
    if enumerated:
        name = enumerated["title"]
        if not WORD_TEST.search(name) or (
            level is None
            and (name.endswith((".", "。", ";", "；")) or len(name.split()) > 13)
        ):
            return None
        level = level if level is not None else 1 + enumerated["number"].count(".")
        line = name
    else:
        cn = CN_NUMBER.fullmatch(line)
        if cn:
            line = cn[2]
            level = level or 1
    title = line.strip(" ：:")
    for role, pattern in STANDALONE.items():
        if re.fullmatch(pattern, title, re.I):
            return level if level is not None else 1, title, role
    if APPENDIX.fullmatch(title):
        return level if level is not None else 1, title, "appendix"
    if level is not None:
        return level, title, "section"
    return None


def word_styles(path):
    """Map paragraph numbers used by casework to the document's heading hierarchy."""
    with ZipFile(path) as archive:
        tree = ET.fromstring(archive.read("word/document.xml"))
        styles = {}
        if "word/styles.xml" in archive.namelist():
            st = ET.fromstring(archive.read("word/styles.xml"))
            for style in st.findall(WORD + "style"):
                key = style.get(WORD + "styleId")
                name = style.find(WORD + "name")
                base = style.find(WORD + "basedOn")
                out = style.find("./" + WORD + "pPr/" + WORD + "outlineLvl")
                styles[key] = (
                    (name.get(WORD + "val", "") if name is not None else ""),
                    base.get(WORD + "val") if base is not None else None,
                    int(out.get(WORD + "val")) + 1 if out is not None else None,
                )

        def level(key):
            seen = set()
            while key and key not in seen:
                seen.add(key)
                name, key, rank = styles.get(key, ("", None, None))
                if name.lower() in ("title", "标题"):
                    return 0
                if rank is not None:
                    return rank if 1 <= rank <= 9 else None
                match = re.fullmatch(r"(?:heading|标题)\s*(\d)", name, re.I)
                if match:
                    return int(match[1])
            return None

        table_paras = {
            p for table in tree.iter(WORD + "tbl") for p in table.iter(WORD + "p")
        }
        result = {}
        for i, p in enumerate(tree.iter(WORD + "p"), 1):
            props = p.find(WORD + "pPr")
            rank = None
            if props is not None:
                outline = props.find(WORD + "outlineLvl")
                style = props.find(WORD + "pStyle")
                if outline is not None:
                    rank = int(outline.get(WORD + "val")) + 1
                elif style is not None:
                    rank = level(style.get(WORD + "val"))
            result[f"word/document.xml:p{i}"] = {
                "heading_level": rank,
                "story": "table" if p in table_paras else "body",
            }
        return result


def reading_order(blocks, width):
    """Read each column as prose; wide blocks separate the single-column page bands."""
    center = width / 2

    def side(b):
        left, _, right, _ = b["bbox"]
        if right <= center + 2:
            return "left"
        if left >= center - 2:
            return "right"
        return "wide"

    candidates = {
        s: [b for b in blocks if side(b) == s and len(b["text"]) > 70]
        for s in ("left", "right")
    }
    if not all(candidates.values()):
        return sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    ordered = []
    pending = []

    def flush():
        for col in ("left", "right"):
            ordered.extend(
                sorted(
                    (b for b in pending if side(b) == col),
                    key=lambda b: (b["bbox"][1], b["bbox"][0]),
                )
            )
        pending.clear()

    for b in sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0])):
        if side(b) == "wide":
            flush()
            ordered.append(b)
        else:
            pending.append(b)
    flush()
    return ordered


def pdf_blocks(path):
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            return None
    result = []
    margin_keys = defaultdict(set)
    with fitz.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("encrypted PDF")
        for n, page in enumerate(doc, 1):
            blocks = []
            title_box = None
            if n == 1:
                candidates = []
                for block in page.get_text("dict")["blocks"]:
                    spans = [
                        s
                        for line in block.get("lines", [])
                        for s in line["spans"]
                        if s["text"].strip()
                    ]
                    txt = " ".join(s["text"] for s in spans).strip()
                    if (
                        spans
                        and block["bbox"][1] < page.rect.height * 0.4
                        and 15 < len(txt) < 270
                        and "@" not in txt
                    ):
                        candidates.append(
                            (
                                max(s["size"] for s in spans),
                                tuple(round(v, 2) for v in block["bbox"]),
                            )
                        )
                if candidates and max(candidates)[0] >= 14:
                    title_box = max(candidates)[1]
            for x0, y0, x1, y1, text, number, kind in page.get_text(
                "blocks", sort=False
            ):
                if kind or not text.strip():
                    continue
                text = text.rstrip("\n")
                box = [round(x, 2) for x in (x0, y0, x1, y1)]
                key = folded(re.sub(r"\d+", "#", text))
                margin = (
                    y1 < page.rect.height * 0.09 or y0 > page.rect.height * 0.91
                ) and len(text) < 230
                if margin:
                    margin_keys[key].add(n)
                blocks.append(
                    {
                        "text": text,
                        "bbox": box,
                        "page": n,
                        "location": f"p{n}:B{number + 1}",
                        "margin_key": key if margin else None,
                        "heading_level": 0 if tuple(box) == title_box else None,
                    }
                )
            result.append((n, reading_order(blocks, page.rect.width)))
    for _, blocks in result:
        for b in blocks:
            key = b.pop("margin_key")
            if key and len(margin_keys[key]) >= 2:
                b["story"] = "running"
    return result
