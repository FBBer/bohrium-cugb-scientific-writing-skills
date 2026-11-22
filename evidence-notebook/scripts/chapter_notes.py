"""Choose source-located notes in a paper's own section order."""

import re
from collections import defaultdict
from pathlib import Path
from paper_structure import folded, heading_info

ROLE_CUES = {
    "limitation": r"\b(?:limited to|limited by|appl(?:ies|y) only|only (?:included|considered|tested|covered|during|under)|(?:under|in|from) [^.]{0,35}\bonly\b|(?:estimate|value|result|analysis|comparison) excludes|did not (?:test|measure|evaluate|include)|not (?:tested|measured|evaluated)|could not|remains? (?:unclear|unknown)|cannot be (?:generalized|generalised))\b|仅(?:限|适用|覆盖|在)|未(?:覆盖|评估|验证|测试)|没有覆盖|局限在|不适用于",
    "interpretation": r"\b(?:we (?:suggest|hypothesi[sz]e|speculate)|may reflect|might be due|may (?:explain|indicate)|suggests? that|could be attributed)\b|作者推测|可能归因于|提示|可能反映",
    "question": r"\b(?:we (?:asked|examined|investigated) whether|research question|(?:aim(?:ed)?|objective)(?: of [^.]{0,32})? (?:is |was )?(?:to|whether)|we seek to)\b|旨在|研究目的是|研究问题|考察是否",
    "finding": r"\b(?:achiev(?:e|es|ed)|outperform\w*|decreased|increased|unchanged|found that|was observed|observed (?:offset|bias|difference)|median (?:error|bias)|(?:error|bias|lag|offset|difference|uncertaint(?:y|ies)) (?:was|were|of)|results? in|improves?|yields?|reduc(?:es|ed))\b|偏差(?:为|是)|误差(?:为|是)|升至|降至|下降|减少|增加|观测到|无显著|中位数为",
    "method": r"\b(?:we (?:sampled|collected|trained|compared|evaluate[d]?|propose|measured|used)|participants|replicates|recorded independently|were (?:recorded|assigned)|prespecified|using [^.]{0,36} (?:measurements|observations)|dataset is coupled|dataset (?:comprised|contained)|data from)\b|采样|采集|采用|每隔|重复测量|实验设计|记录测点",
}
PATTERNS = {key: re.compile(val, re.I) for key, val in ROLE_CUES.items()}
EXTERNAL = re.compile(
    r"^(?:(?:a |an |the )?(?:prior|previous|earlier|published) (?:survey|work|study|studies|reports?)|前人研究|以往研究|既有研究)",
    re.I,
)
QUALIFIER = re.compile(
    r"^(?:(?:this|these|the) (?:effect|estimate|value|finding|result|improvement|comparison|analysis|pattern)s?\b|only (?:at|under|during)|(?:本|该)(?:效应|数值|估计|结果|结论)|这一(?:结果|现象)|上述(?:结果|结论))",
    re.I,
)
BOUNDARY = re.compile(
    r"[。！？!?]+(?:[”’\"])?(?=\s|[\u3400-\u9fff]|$)|[.](?=\s+(?:[A-Z0-9“\"(\u3400-\u9fff])|$)"
)
ABBREVIATION = re.compile(
    r"(?:\b(?:figs?|eqs?|refs?|sec|secs|no|dr|prof|vs|al|e\.g|i\.e|cf)|(?-i:\b[A-Z]))\.$",
    re.I,
)
INLINE_ABSTRACT = re.compile(r"^\s*(abstract|summary|摘要)\s*[.:：—–]\s*", re.I)


def sentence_offsets(text, lo, hi):
    start = lo
    for m in BOUNDARY.finditer(text, lo, hi):
        if m.group() == "." and ABBREVIATION.search(text[start : m.end()]):
            continue
        left = start + len(text[start : m.end()]) - len(text[start : m.end()].lstrip())
        if left < m.end():
            yield left, m.end()
        start = m.end()
    while start < hi and text[start].isspace():
        start += 1
    while hi > start and text[hi - 1].isspace():
        hi -= 1
    if start < hi:
        yield start, hi


def classify(quote, section_role):
    q = folded(quote)
    if EXTERNAL.search(q):
        return "context", True
    cues = [key for key, expr in PATTERNS.items() if expr.search(q)]
    if cues and cues[0] in ("limitation", "interpretation", "question"):
        return cues[0], False
    if section_role in ("finding", "method") and section_role in cues:
        return section_role, False
    if cues:
        return cues[0], False
    if section_role in (
        "method",
        "finding",
        "interpretation",
        "limitation",
        "question",
    ):
        return section_role, False
    return "context", False


def recognize(row):
    """Return ordered runs of prose and titles, with offsets into the unmodified source block."""
    text = row["text"]
    style = row.get("heading_level")
    if style is not None:
        title = heading_info(text, style)
        if title:
            yield "title", 0, len(text), title
            return
    if row.get("bbox"):
        # Split PDF headings only when the entire physical block is a plausible title.
        # A short numeric line inside an equation or table must never change the section.
        title = heading_info(text)
        if title and len(text.splitlines()) <= 3:
            yield "title", 0, len(text), title
            return
        prefix = INLINE_ABSTRACT.match(text)
        if prefix:
            yield "title", 0, prefix.end(), (1, prefix[1], "abstract")
            yield "text", prefix.end(), len(text), None
            return
        yield "text", 0, len(text), None
        return
    pos = 0
    for match in re.finditer(r"[^\n]+", text):
        title = heading_info(match[0])
        if title:
            if pos < match.start():
                yield "text", pos, match.start(), None
            yield "title", match.start(), match.end(), title
            pos = match.end()
        else:
            prefix = INLINE_ABSTRACT.match(match[0])
            if prefix:
                if pos < match.start():
                    yield "text", pos, match.start(), None
                pos = match.start() + prefix.end()
                yield "title", match.start(), pos, (1, prefix[1], "abstract")
    if pos < len(text):
        yield "text", pos, len(text), None


def extract(rows, file, focus, limit):
    title = Path(file).stem
    chapters = []
    stack = []
    all_notes = []
    for source_no, source in enumerate(rows):
        if source.get("story") in {"table", "running"}:
            continue
        if file.lower().endswith(".docx") and not re.fullmatch(
            r"word/document.xml:p\d+", source["location"]
        ):
            continue
        for kind, lo, hi, meta in recognize(source):
            if kind == "title":
                level, name, mode = meta
                is_title = level == 0 or (
                    source_no == 0
                    and source["text"].lstrip().startswith("# ")
                    and mode == "section"
                )
                if is_title:
                    title = name
                    continue
                # A standalone References or Appendix heading starts a new top-level body part.
                if mode in {"references", "appendix"}:
                    stack.clear()
                while stack and stack[-1]["level"] >= level:
                    stack.pop()
                inherited = stack[-1]["kind"] if stack else "context"
                mode = inherited if mode == "section" else mode
                if stack and stack[-1]["kind"] == "references":
                    mode = "references"
                chapter = {
                    "title": name,
                    "level": level,
                    "kind": mode,
                    "path": [c["title"] for c in stack] + [name],
                    "notes": [],
                }
                stack.append(chapter)
                chapters.append(chapter)
                continue
            if stack and stack[-1]["kind"] == "references":
                continue
            if not stack and (not chapters or chapters[0]["kind"] != "front"):
                # PDF front matter before the abstract is indexed separately, then omitted when a body starts.
                chapters.append(
                    {"title": "", "level": 0, "kind": "front", "path": [], "notes": []}
                )
            ch = stack[-1] if stack else chapters[0]
            for start, end in sentence_offsets(source["text"], lo, hi):
                quote = source["text"][start:end]
                if len(quote.strip()) < 8 or not re.search(
                    r"[A-Za-z]{3}|[\u3400-\u9fff]{2}", quote
                ):
                    continue
                key = folded(quote)
                if not key:
                    continue
                role, external = classify(quote, ch["kind"])
                note = {
                    "source": file,
                    "location": source["location"],
                    "id": source["id"],
                    "start": start,
                    "end": end,
                    "section": ch["title"],
                    "path": ch["path"],
                    "quote": quote,
                    "role": role,
                    "normalized": key,
                    "external": external,
                    "rank": (
                        sum(folded(t) in key for t in focus),
                        int(bool(PATTERNS.get(role) and PATTERNS[role].search(key))),
                        int(bool(re.search(r"\d", key))),
                    ),
                }
                if "page" in source:
                    note.update(page=source["page"], bbox=source["bbox"])
                ch["notes"].append(note)
                all_notes.append(note)
    # Preserve unheaded documents. When the paper has headings, exclude pre-title running material.
    if (
        len(chapters) > 1
        and chapters[0]["kind"] == "front"
        and not any(n["role"] != "context" for n in chapters[0]["notes"])
    ):
        drop = {id(x) for x in chapters[0]["notes"]}
        all_notes = [x for x in all_notes if id(x) not in drop]
        chapters = chapters[1:]
    for ch in chapters:
        previous = None
        for n in ch["notes"]:
            if (
                previous
                and previous["role"] == "finding"
                and n["role"] == "limitation"
                and not n["external"]
            ):
                same_block = n["id"] == previous["id"]
                section_terms = set(
                    re.findall(r"[a-z]{4,}", folded(" ".join(ch["path"])))
                )
                shared_subject = (
                    len(
                        section_terms.intersection(
                            re.findall(r"[a-z]{4,}", n["normalized"])
                        )
                    )
                    >= 2
                )
                if QUALIFIER.search(n["normalized"]) or (same_block and shared_subject):
                    previous["condition_note"] = n
            previous = n
    groups = defaultdict(list)
    for n in all_notes:
        groups[n["role"]].append(n)

    def preferred(notes, cap):
        return sorted(notes, key=lambda n: n["rank"], reverse=True)[:cap]

    selected = {role: preferred(ns, limit) for role, ns in groups.items()}
    picked = {id(n) for ns in selected.values() for n in ns}
    chapter_picks = []
    for ch in chapters:
        if ch["kind"] == "references" or not ch["notes"]:
            continue
        # One or two main passages per original section survive a long document's role budget.
        local = preferred(
            [n for n in ch["notes"] if n["role"] != "context"], min(2, limit)
        )
        if not local:
            local = preferred(ch["notes"], 1)
        picked.update(id(n) for n in local)
        chapter_picks.append(ch)
    for n in all_notes:
        if id(n) in picked and "condition_note" in n:
            picked.add(id(n["condition_note"]))
    chosen = [n for n in all_notes if id(n) in picked]

    def stable(n):
        return f"{n['id']}-{n['start']}-{n['end']}"

    for n in chosen:
        n["anchor"] = stable(n)
        if "condition_note" in n:
            n["conditions"] = [stable(n["condition_note"])]
        for k in ("condition_note", "rank", "normalized"):
            n.pop(k, None)
    chosen_ids = {id(n) for n in chosen}
    outline = [
        {
            "title": ch["title"],
            "level": ch["level"],
            "path": ch["path"],
            "anchors": [n["anchor"] for n in ch["notes"] if id(n) in chosen_ids],
        }
        for ch in chapter_picks
    ]
    by_role = {
        role: [n for n in groups[role] if id(n) in {id(x) for x in selected[role]}]
        for role in groups
    }
    return {"title": title, "sections": by_role, "outline": outline, "notes": chosen}
