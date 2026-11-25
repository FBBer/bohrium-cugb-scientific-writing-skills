"""Build a reusable notebook from research papers and optional named data tables."""

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from urllib.parse import quote
import io
from collections import defaultdict
from pathlib import Path
from casework import prepare, write, atomic_text
from chapter_notes import extract
from study_tables import collect_tables
from notebook_reader import (
    compact,
    issue_label,
    join_passage,
    passage_groups,
    render as render_html,
)
from notebook_publish import publish

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
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".reading-") as root:
        staged = Path(root) / "new"
        result = build(
            folder, out, staged, selected, focus, limit, language, table_links
        )
        publish(staged, out)
    return result


def build(folder, out, staged, selected, focus, limit, language, table_links):
    idx = prepare(folder, staged / "work", reading_layout=True)
    available = {
        f["path"]
        for f in idx["files"]
        if Path(f["path"]).suffix.lower() in PROSE and f["path"] != "task.md"
    }
    files = set(selected) if selected else available
    if files - available:
        raise ValueError("Unknown paper: " + ", ".join(sorted(files - available)))
    if not files:
        raise ValueError("No supported paper files in the input directory.")
    cards = collect(idx, files, focus, limit)
    tables = collect_tables(folder, files, table_links, idx)
    lookup = {r["id"]: r for r in idx["sources"]}
    en = language == "en"
    labels = LABELS[language]
    body = []
    refs = []
    limits = []
    coverage = {}
    count = 0
    rows = [
        [
            "paper",
            "role",
            "section",
            "source",
            "location",
            "start",
            "end",
            "quote",
            "anchor",
            "condition_anchors",
            "condition_quotes",
            "condition_locations",
        ]
    ]
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
        if not card["notes"] and not card["source_issues"]:
            card["source_issues"].append(
                {"file": file, "reason": "no eligible prose passages"}
            )
        status = (
            "unreadable"
            if not card["notes"]
            else "partial"
            if card["source_issues"]
            else "read"
        )
        card["read_status"] = status
        for issue in card["source_issues"]:
            location = issue.get("location", "")
            target = card["original_href"]
            page = re.fullmatch(r"p(\d+)", location)
            if page:
                target += "#page=" + page[1]
            label = file + (" · " + location if location else "")
            limits.append(
                f"- [{label}](<{target}>) — {issue_label(issue['reason'], en)}"
            )
        coverage[file] = {
            "status": status,
            "source_sha256": card["source_sha256"],
            "issues": card["source_issues"],
            "passages": len(card["notes"]),
        }
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
                conditions = [items[key] for key in r.get("conditions", [])]
                scope = "Scope" if en else "适用条件"
                following = "".join(
                    f" · [{scope}](#note-{q['anchor']})" for q in conditions
                )
                target = card["original_href"] + (
                    f"#page={r['page']}" if r.get("page") else ""
                )
                refs.append(
                    f'<a id="ref-{count}"></a>〔{count}〕 [{file} · {r["location"]}](<{target}>) · {r["start"]}–{r["end"]}{following}'
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
                        a,
                        json.dumps(
                            [q["anchor"] for q in conditions], ensure_ascii=False
                        ),
                        json.dumps(
                            [q["quote"] for q in conditions], ensure_ascii=False
                        ),
                        json.dumps(
                            [q["location"] for q in conditions], ensure_ascii=False
                        ),
                    ]
                )
            for group in passage_groups(ch["anchors"], items, lookup):
                raw = lookup[group[0]["id"]]["text"]

                def markdown_note(note):
                    return f'<a id="note-{note["anchor"]}"></a>' + compact(
                        note["quote"]
                    )

                citations = " ".join(
                    f"[〔{n['reference']}〕](#ref-{n['reference']})" for n in group
                )
                body.append(join_passage(group, raw, markdown_note) + " " + citations)
        matrix.append(
            [
                file,
                *[
                    " | ".join(
                        " · ".join(
                            f"{compact(q['quote'])} 〔{q['reference']}〕"
                            for q in [r, *(items[k] for k in r.get("conditions", []))]
                        )
                        for r in card["sections"].get(axis, [])
                    )
                    for axis in axes
                ],
            ]
        )
    for t in tables.values():
        t["source_sha256"] = sha_file(folder / t["source"])
        t["original_href"] = quote(os.path.relpath(folder / t["source"], out), safe="/")
    if refs:
        body.extend(["## " + ("Source locations" if en else "原文位置"), *refs])
    if limits:
        body.extend(
            ["## " + ("Pages to consult" if en else "需查阅的原文"), "\n".join(limits)]
        )
    status = "unreadable" if not count else "partial" if limits else "complete"
    write(staged / "coverage.json", {"status": status, "papers": coverage})
    atomic_text(staged / "notes.md", "\n\n".join(body) + "\n")
    atomic_text(staged / "comparison.tsv", tsv(rows))
    atomic_text(staged / "study-matrix.tsv", tsv(matrix))
    atomic_text(staged / "notebook.html", render_html(cards, tables, lookup, en=en))
    write(staged / "reading-cards.json", cards)
    write(staged / "tables.json", tables)
    return sum(bool(card["notes"]) for card in cards.values()), count


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
    except (OSError, ValueError, csv.Error) as exc:
        p.exit(2, f"{exc}\n")
    if not passages:
        p.exit(
            2,
            "No readable passages. See coverage.json or notebook.html for the original files and pages.\n",
        )
    print(f"{papers} papers, {passages} located passages")
