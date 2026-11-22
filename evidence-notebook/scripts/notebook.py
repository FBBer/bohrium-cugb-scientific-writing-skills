"""Build a reusable notebook from research papers and optional named data tables."""

import argparse
import csv
import hashlib
import os
from urllib.parse import quote
import io
from collections import defaultdict
from pathlib import Path
from casework import prepare, write, atomic_text
from chapter_notes import extract
from study_tables import collect_tables
from notebook_reader import compact, render as render_html

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


def collect(index, files, focus, limit):
    papers = defaultdict(list)
    for record in index["sources"]:
        if record["source"] in files:
            papers[record["source"]].append(record)
    return {name: extract(papers[name], name, focus, limit) for name in sorted(files)}


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tsv(rows):
    text = io.StringIO()
    csv.writer(text, delimiter="\t", lineterminator="\n").writerows(rows)
    return text.getvalue()


def render(folder, out, selected, focus, limit, language, table_links=()):
    folder, out = folder.resolve(), out.resolve()
    if folder == out or folder in out.parents:
        raise ValueError("Choose an output directory outside the source papers.")
    idx = prepare(folder, out / "work", reading_layout=True)
    available = {
        r["source"] for r in idx["sources"] if Path(r["source"]).suffix.lower() in PROSE
    }
    files = set(selected) if selected else available
    if not files or files - available:
        raise ValueError(
            "Select readable papers by their paths relative to the input folder."
        )
    cards = collect(idx, files, focus, limit)
    tables = collect_tables(folder, files, table_links, idx)
    lookup = {r["id"]: r for r in idx["sources"]}
    en = language == "en"
    labels = LABELS[language]
    body = []
    refs = []
    count = 0
    rows = [["paper", "role", "section", "source", "location", "start", "end", "quote"]]
    axes = ("question", "method", "finding", "interpretation", "limitation")
    matrix = [["paper", *(labels[axis] for axis in axes)]]
    for file, card in cards.items():
        card["source_sha256"] = sha_file(folder / file)
        card["original_href"] = quote(os.path.relpath(folder / file, out), safe="/")
        card["uncovered"] = [
            k
            for k in ("question", "method", "finding", "limitation")
            if not card["sections"].get(k)
        ]
        card["table_files"] = [f for f, t in tables.items() if t["paper"] == file]
        card["source_issues"] = [
            i for i in idx.get("issues", []) if i.get("file") == file
        ]
        items = {r["anchor"]: r for r in card["notes"]}
        body.extend(["# " + card["title"], file])
        for ch in card["outline"]:
            name = " › ".join(ch["path"])
            if name:
                body.append("## " + name)
            for a in ch["anchors"]:
                r = items[a]
                count += 1
                r["reference"] = count
                context = lookup[r["id"]]["text"]
                if context[r["start"] : r["end"]] != r["quote"]:
                    raise ValueError("Source quote mismatch")
                body.append(
                    f"**{labels[r['role']]}**　{compact(r['quote'])} [〔{count}〕](#ref-{count})"
                )
                refs.append(
                    f'<a id="ref-{count}"></a>〔{count}〕 {file} · {r["location"]} · {r["start"]}–{r["end"]}'
                )
                rows.append(
                    [
                        file,
                        r["role"],
                        r["section"],
                        file,
                        r["location"],
                        r["start"],
                        r["end"],
                        r["quote"],
                    ]
                )
        matrix.append(
            [
                file,
                *[
                    " | ".join(
                        f"{compact(r['quote'])} 〔{r['reference']}〕"
                        for r in card["sections"].get(axis, [])
                    )
                    for axis in axes
                ],
            ]
        )
    if not count:
        raise ValueError("No prose passages found in the selected sources.")
    for t in tables.values():
        t["source_sha256"] = sha_file(folder / t["source"])
    body.extend(["## " + ("Source locations" if en else "原文位置"), *refs])
    atomic_text(out / "notes.md", "\n\n".join(body) + "\n")
    atomic_text(out / "comparison.tsv", tsv(rows))
    atomic_text(out / "study-matrix.tsv", tsv(matrix))
    atomic_text(out / "notebook.html", render_html(cards, tables, lookup, labels, en))
    write(out / "reading-cards.json", cards)
    write(out / "tables.json", tables)
    return len(cards), count


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("materials", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--paper", action="append", default=[])
    p.add_argument("--focus", action="append", default=[])
    p.add_argument("--per-role", type=int, default=3)
    p.add_argument("--language", choices=LABELS, default="zh")
    p.add_argument("--table", action="append", default=[], metavar="PAPER=TABLE")
    a = p.parse_args()
    if not 1 <= a.per_role <= 20:
        p.error("--per-role must be between 1 and 20")
    try:
        papers, passages = render(
            a.materials, a.output, a.paper, a.focus, a.per_role, a.language, a.table
        )
    except (OSError, ValueError) as exc:
        p.exit(2, f"{exc}\n")
    print(f"{papers} papers, {passages} located passages")
