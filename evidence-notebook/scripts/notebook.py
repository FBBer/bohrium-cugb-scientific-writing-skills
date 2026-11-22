"""Build a reading notebook and a cross-paper evidence table from the papers themselves."""

import argparse
from collections import defaultdict
import csv
import io
from pathlib import Path
import re
from casework import prepare, write, atomic_text

HEADINGS = {
    "question": r"abstract|background|objectives?|research question|introduction|摘要|研究问题|研究目的|引言|背景",
    "method": r"(?:materials?(?: and methods?)?|methods?|methodology|experiment(?:al setup)?|data(?:set)?s?|protocol)|材料与方法|研究方法|实验设置|数据与方法|研究设计|方法|数据",
    "finding": r"results?(?: and discussion)?|findings?|observations?|结果(?:与讨论)?|主要发现|研究结果|实验结果",
    "interpretation": r"discussion|interpretation|conclusions?|讨论|结论|作者解释",
    "limitation": r"limitations?(?: and future work)?|scope|limitations? of (?:this|the) study|局限(?:性)?|研究局限|适用范围|限制",
    "references": r"references|bibliography|acknowledg(?:e)?ments?|参考文献|致谢",
}
CUES = {
    k: re.compile(v, re.I)
    for k, v in {
        "limitation": r"\b(?:only (?:included|considered|tested|covered|indoors|at|in)|limited to|limitation|cannot|could not|did not (?:test|measure|evaluate)|not (?:tested|measured|evaluated)|remain(?:s)? (?:unclear|unknown))\b|未(?:测|验证|评估)|局限|仅适用|仅限|尚不清楚",
        "question": r"\b(?:objective|research question|aim(?:ed)? to|investigat\w* whether|asked whether)\b|研究目的是|研究问题|旨在|考察是否",
        "method": r"\b(?:sampled|randomi[sz]ed|protocol|measured using|participants|replicates)\b|采用|重复测量|实验设计|采样",
        "finding": r"\b(?:increased|decreased|reduced|observed|found|unchanged|remained)\b|升至|下降|降低|观测到|无显著|增加",
        "interpretation": r"\b(?:suggests?|hypothesi[sz]e|may reflect|might be due)\b|推测|可能归因于|提示",
    }.items()
}
LABELS = {
    "zh": {
        "question": "研究问题",
        "method": "数据与方法",
        "finding": "主要发现",
        "interpretation": "作者解释",
        "limitation": "适用范围与局限",
        "context": "原文摘录",
    },
    "en": {
        "question": "Research question",
        "method": "Data and methods",
        "finding": "Findings",
        "interpretation": "Authors’ interpretation",
        "limitation": "Scope and limitations",
        "context": "Source passages",
    },
}
PROSE = {".md", ".txt", ".pdf", ".docx", ".tex", ".rst"}
SENTENCE_BREAK = re.compile(r'(?<=[。！？!?])\s*|(?<=\.)\s+(?=[A-Z0-9“"\u3400-\u9fff])')


def heading(line):
    line = line.strip()
    marked = line.startswith("#")
    clean = re.sub(r"^#{1,6}\s*", "", line)
    clean = re.sub(r"^(?:\d+(?:\.\d+)*[.)]?|[IVX]+\.)\s+", "", clean).strip(" ：:")
    if len(clean) > 105:
        return None
    for role, expr in HEADINGS.items():
        if re.fullmatch(expr, clean, re.I):
            return clean, role
    return (clean, "context") if marked and clean else None


def spans(raw, start, stop):
    left = start
    for boundary in SENTENCE_BREAK.finditer(raw, start, stop):
        yield left, boundary.start()
        left = boundary.end()
    yield left, stop


def collect(index, files, focus, limit):
    groups = defaultdict(lambda: defaultdict(list))
    states = {}
    titles = {}
    seen = defaultdict(set)
    for source in index["sources"]:
        file = source["source"]
        if file not in files:
            continue
        text = source["text"]
        section, role = states.get(file, ("", "context"))
        chunk = 0

        def add(start, stop):
            if role == "references":
                return
            for lo, hi in spans(text, start, stop):
                q = text[lo:hi].strip()
                lo += len(text[lo:hi]) - len(text[lo:hi].lstrip())
                hi = lo + len(q)
                if len(q) < 8 or q in seen[file] or not any(c.isalpha() for c in q):
                    continue
                cues = [k for k, expr in CUES.items() if expr.search(q)]
                # A limitation in a results paragraph remains a limitation. Numbers in methods remain methods.
                assigned = (
                    "limitation"
                    if "limitation" in cues
                    else role
                    if role != "context"
                    else cues[0]
                    if cues
                    else "context"
                )
                rank = (
                    sum(t.casefold() in q.casefold() for t in focus),
                    int(assigned in cues),
                    int(bool(re.search(r"\d", q))),
                    -len(groups[file][assigned]),
                )
                seen[file].add(q)
                groups[file][assigned].append(
                    (
                        rank,
                        {
                            "source": file,
                            "location": source["location"],
                            "id": source["id"],
                            "start": lo,
                            "end": hi,
                            "section": section,
                            "quote": q,
                        },
                    )
                )

        for match in re.finditer(r"[^\n]+", text):
            label = heading(match[0])
            if label is None:
                continue
            add(chunk, match.start())
            section, role = label
            chunk = match.end()
            if role == "context" and match[0].lstrip().startswith("# "):
                titles.setdefault(file, section)
        add(chunk, len(text))
        states[file] = (section, role)
    result = {}
    for file in sorted(files):
        picked = {}
        for role, rows in groups[file].items():
            best = sorted(rows, key=lambda x: x[0], reverse=True)[:limit]
            chosen = {id(r) for _, r in best}
            picked[role] = [r for _, r in rows if id(r) in chosen]
        result[file] = {"title": titles.get(file, Path(file).stem), "sections": picked}
    return result


def render(folder, out, selected, focus, limit, language):
    folder = folder.resolve()
    out = out.resolve()
    if folder == out or folder in out.parents:
        raise ValueError("Choose an output directory outside the source papers.")
    idx = prepare(folder, out / "work")
    available = {
        r["source"] for r in idx["sources"] if Path(r["source"]).suffix.lower() in PROSE
    }
    files = set(selected) if selected else available
    if not files or files - available:
        raise ValueError(
            "Select readable papers by their paths relative to the input folder."
        )
    cards = collect(idx, files, focus, limit)
    labels = LABELS[language]
    body = []
    table = io.StringIO()
    cols = csv.writer(table, delimiter="\t", lineterminator="\n")
    cols.writerow(
        ["paper", "role", "section", "source", "location", "start", "end", "quote"]
    )
    counter = 0
    for file, card in cards.items():
        body.append("# " + card["title"])
        body.append(file)
        for role, title in labels.items():
            rows = card["sections"].get(role, [])
            if not rows:
                continue
            body.append("## " + title)
            for r in rows:
                counter += 1
                r["reference"] = counter
                quote = " ".join(r["quote"].split())
                body.append(f"{quote} 〔{counter}〕")
                cols.writerow(
                    [
                        file,
                        role,
                        r["section"],
                        r["source"],
                        r["location"],
                        r["start"],
                        r["end"],
                        r["quote"],
                    ]
                )
        card["uncovered"] = [
            k
            for k in ("question", "method", "finding", "limitation")
            if not card["sections"].get(k)
        ]
    if not counter:
        raise ValueError("No prose passages found in the selected sources.")
    body.append("## " + ("原文位置" if language == "zh" else "Source locations"))
    for card in cards.values():
        for role in labels:
            for r in card["sections"].get(role, []):
                body.append(
                    f"〔{r['reference']}〕 {r['source']} · {r['location']} · {r['start']}–{r['end']}"
                )
    atomic_text(out / "notes.md", "\n\n".join(body) + "\n")
    atomic_text(out / "comparison.tsv", table.getvalue())
    matrix = io.StringIO()
    sheet = csv.writer(matrix, delimiter="\t", lineterminator="\n")
    axes = ("question", "method", "finding", "interpretation", "limitation")
    sheet.writerow(["paper", *(labels[axis] for axis in axes)])
    for file, card in cards.items():
        cells = []
        for axis in axes:
            cells.append(
                " | ".join(
                    f"{' '.join(r['quote'].split())} 〔{r['reference']}〕"
                    for r in card["sections"].get(axis, [])
                )
            )
        sheet.writerow([file, *cells])
    atomic_text(out / "study-matrix.tsv", matrix.getvalue())
    write(out / "reading-cards.json", cards)
    return len(cards), counter


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("materials", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--paper", action="append", default=[])
    p.add_argument("--focus", action="append", default=[])
    p.add_argument("--per-role", type=int, default=3)
    p.add_argument("--language", choices=LABELS, default="zh")
    a = p.parse_args()
    if not 1 <= a.per_role <= 20:
        p.error("--per-role must be between 1 and 20")
    try:
        papers, passages = render(
            a.materials, a.output, a.paper, a.focus, a.per_role, a.language
        )
    except (OSError, ValueError) as exc:
        p.exit(2, f"{exc}\n")
    print(f"{papers} papers, {passages} located passages")
