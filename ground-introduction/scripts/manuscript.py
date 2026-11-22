"""Compile an annotated draft into a manuscript, bibliography and sentence-level source map."""

import argparse
from collections import defaultdict
import csv
import io
from pathlib import Path
import re
from casework import prepare, atomic_text, write, read
from compose import absent_measurements

KEY = r"[A-Za-z0-9_-]+"
REF = re.compile(r"\[\^(" + KEY + r")\]")
GROUP = re.compile(r"\[\^" + KEY + r"\](?:[ \t]*\[\^" + KEY + r"\])*")
DEFINITION = re.compile(r"^\[\^(" + KEY + r")\]:\s*([^|]+?)\s*\|\s*(.+?)\s*$")
ROLES = {
    "background": r"background|introduction|research (?:context|background)|引言|背景|研究背景",
    "related": r"related work|prior (?:studies|work)|comparison|相关工作|文献比较|已有工作",
    "gap": r"research gap|gap|open question|研究空白|待解问题|研究缺口",
    "contribution": r"(?:our |study )?contributions?|present (?:work|study)|本文工作|贡献|本文贡献",
}
LIMIT = re.compile(
    r"\b(?:only|limited|excluded|restricted|unmeasured|unknown|unexplored|remain\w*|did not|not (?:measured|examined|tested|included|evaluated|assessed|reported))\b|仅|局限|未(?:测|评|检|考|涵|研究|覆盖|报告)|限于",
    re.I,
)
UNBOUNDED = re.compile(
    r"\b(?:no (?:prior|previous) (?:work|stud(?:y|ies))|(?:first|only) (?:ever|in the world)|all previous (?:studies|work)|never been (?:studied|investigated))\b|全球首[个次]|所有(?:已有|现有)研究|从未有(?:人|研究)|首次在世界",
    re.I,
)
PUNCT = re.compile(r"^[\s.,，。；;:：!?！？、)）”’]*$")
SENTENCE_END = re.compile(r"[。！？!?]+|\.(?!\d)")
ABBREVIATION = re.compile(r"(?i:\b(?:fig|eq|dr|no|vol|al|vs|e\.g|i\.e))$|\b[A-Z]$")
CAUSAL = re.compile(r"\b(?:causes?|caused|leads? to|led to|results? in|resulted in)\b|导致|引起|造成", re.I)
ASSOCIATION = re.compile(r"\b(?:associat\w*|correlat\w*)\b|相关|关联", re.I)
NONCAUSAL = re.compile(r"\b(?:cannot|could not|does not|did not|cannot be used to) (?:establish|infer|prove|show) caus|不能(?:推断|证明|确定)因果", re.I)


def draft_sentences(line):
    """Keep notes with their sentence, whether the author placed them before or after the stop."""
    if not line.strip() or line.lstrip().startswith("#"):
        return [line]
    start = 0
    parts = []
    for stop in SENTENCE_END.finditer(line):
        if stop.start() < start:
            continue
        if stop[0] == "." and ABBREVIATION.search(line[:stop.start()]):
            continue
        end = stop.end()
        while end < len(line) and line[end] in '”’")）':
            end += 1
        note = GROUP.match(line, end + len(line[end:]) - len(line[end:].lstrip()))
        if note:
            end = note.end()
        rest = line[end:]
        if rest and not (rest[0].isspace() or re.match(r"[\u3400-\u9fff]", rest)):
            continue
        parts.append(line[start:end].strip())
        start = end
    tail = line[start:].strip()
    if tail:
        parts.append(tail)
    return parts


DIRECTION = re.compile(
    r"\b(increas(?:e|ed|es)|rose|grew|decreas(?:e|ed|es)|fell|reduc(?:e|ed|es))\b|升高|升至|上升|增加|降低|降至|下降|减少",
    re.I,
)


def reported_directions(text):
    directions = set()
    for match in DIRECTION.finditer(text):
        term = match[0].casefold()
        up = term.startswith("increas") or term in {
            "rose",
            "grew",
            "升高",
            "升至",
            "上升",
            "增加",
        }
        negated = bool(
            re.search(
                r"(?:\bnot|\bnever|\bno evidence of|没有|未(?:见|能)?)\s*$",
                text[max(0, match.start() - 22) : match.start()],
                re.I,
            )
        )
        directions.add((up, negated))
    return directions


def section_role(title):
    label = re.sub(r"^[\d.、)） \t]+", "", title.strip())
    for role, expr in ROLES.items():
        if re.fullmatch(expr, label, re.I):
            return role
    return "background"


def resolve(source, quote, by_file):
    path, sep, locator = source.partition("#")
    rows = by_file.get(path, [])
    if not rows:
        return None, "unknown source " + path
    pattern = re.compile(r"\s+".join(re.escape(w) for w in quote.split()))
    matches = []
    for row in rows:
        if sep and row["location"] != locator:
            continue
        for m in pattern.finditer(row["text"]):
            matches.append(
                {
                    "source": path,
                    "location": row["location"],
                    "id": row["id"],
                    "start": m.start(),
                    "end": m.end(),
                    "quote": m[0],
                }
            )
    if len(matches) == 1:
        return matches[0], None
    return None, (
        "quotation not found"
        if not matches
        else "quotation has multiple matches; specify #location or a longer quotation"
    ) + " in " + source


def compile_draft(materials, draft, out, own, bibliography, language):
    materials = materials.resolve()
    out = out.resolve()
    if out == materials or materials in out.parents:
        raise ValueError("Place the output outside the source folder.")
    if materials in draft.resolve().parents:
        raise ValueError("Keep the annotated draft outside the source papers.")
    idx = prepare(materials, out / "work")
    by_file = defaultdict(list)
    for row in idx["sources"]:
        by_file[row["source"]].append(row)
    missing = set(own) - set(by_file)
    if missing:
        raise ValueError("Missing own-work source: " + ", ".join(sorted(missing)))
    sources = {}
    errors = {}
    declarations = set()
    content = []
    for n, line in enumerate(draft.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = DEFINITION.fullmatch(line.strip())
        if not match:
            if line.lstrip().startswith("[^") and "]: " in line:
                raise ValueError(f"Invalid source definition on line {n}")
            content.extend((n, sentence) for sentence in draft_sentences(line))
            continue
        key, source, quote = match.groups()
        if key in declarations:
            raise ValueError("Duplicate source note " + key)
        declarations.add(key)
        ref, error = resolve(source.strip(), quote, by_file)
        if error:
            errors[key] = error
        else:
            sources[key] = ref
    numbers = {}
    sections = []
    role = "background"
    claims = []
    issues = []
    prose = []
    represented = set()
    previous_prose_line = None
    for n, line in content:
        if not line.strip():
            prose.append("")
            continue
        title = re.fullmatch(r"\s*(#{1,6})\s+(.+?)\s*", line)
        if title:
            role = section_role(title[2])
            sections.append(title[2])
            prose.append(line)
            continue
        cursor = 0
        accepted = []
        line_claims = []
        failures = []
        matches = list(GROUP.finditer(line))
        for mark in matches:
            clause = line[cursor : mark.start()].strip()
            cursor = mark.end()
            keys = list(dict.fromkeys(REF.findall(mark[0])))
            refs = [sources[k] for k in keys if k in sources]
            reasons = [
                errors.get(k, "undefined source note " + k)
                for k in keys
                if k not in sources
            ]
            filenames = {r["source"] for r in refs}
            if not clause or PUNCT.fullmatch(clause):
                reasons.append("empty claim")
            if role == "contribution" and (not own or filenames - set(own)):
                reasons.append("a contribution must cite this study’s own material")
            if role == "gap":
                if not filenames - set(own):
                    reasons.append("the gap needs a prior study")
                if UNBOUNDED.search(clause):
                    reasons.append(
                        "the supplied literature cannot establish a universal gap"
                    )
                if not any(
                    LIMIT.search(r["quote"]) for r in refs if r["source"] not in own
                ):
                    reasons.append(
                        "no cited prior passage states the scope or limitation"
                    )
            values = absent_measurements(clause, " ".join(r["quote"] for r in refs))
            if values:
                reasons.append(
                    "measurement absent from this clause’s sources: "
                    + ", ".join(values)
                )
            quotes = " ".join(r["quote"] for r in refs)
            if (CAUSAL.search(clause) and not NONCAUSAL.search(clause)
                    and (ASSOCIATION.search(quotes) or NONCAUSAL.search(quotes))
                    and (not CAUSAL.search(quotes) or NONCAUSAL.search(quotes))):
                reasons.append("the cited passage describes an association and does not establish this cause")
            observed = reported_directions(" ".join(r["quote"] for r in refs))
            asserted = reported_directions(clause)
            if (
                role != "gap"
                and len(observed) == 1
                and asserted
                and not asserted.issubset(observed)
            ):
                reasons.append(
                    "the reported change or its negation differs from the cited passage"
                )
            if (
                len(filenames) > 1
                and re.search(r"\d", clause)
                and any(
                    absent_measurements(
                        clause, " ".join(r["quote"] for r in refs if r["source"] == f)
                    )
                    for f in filenames
                )
            ):
                reasons.append("attach each study’s measurement to its own clause")
            if reasons:
                failures.extend(reasons)
            accepted.append((clause, refs))
            line_claims.append(
                {"line": n, "role": role, "claim": clause, "evidence": refs}
            )
        tail = line[cursor:].strip()
        if not matches or not PUNCT.fullmatch(tail):
            failures.append("a factual clause has no source note")
        if failures:
            issues.append(
                {"line": n, "draft": line, "reasons": list(dict.fromkeys(failures))}
            )
            continue
        rendered = []
        for clause, refs in accepted:
            cited = []
            for ref in refs:
                file = ref["source"]
                if file in own:
                    continue
                if file not in numbers:
                    numbers[file] = len(numbers) + 1
                if numbers[file] not in cited:
                    cited.append(numbers[file])
            citation = (" [" + ", ".join(map(str, cited)) + "]") if cited else ""
            terminal = re.search(r"([.,;:!?。！？；，：]+)$", clause)
            if terminal:
                clause = clause[: terminal.start()] + citation + terminal[0]
            else:
                clause += citation
            rendered.append(clause)
        sentence = " ".join(rendered) + tail
        if previous_prose_line == n:
            prose[-1] += ("" if re.match(r"[\u3400-\u9fff]", sentence) else " ") + sentence
        else:
            prose.append(sentence)
        previous_prose_line = n
        claims.extend(line_claims)
        represented.add(role)
    if numbers:
        prose.extend(
            ["", "## " + ("参考文献" if language == "zh" else "References"), ""]
        )
        prose.extend(
            f"[{n}] {bibliography.get(file, file)}" for file, n in numbers.items()
        )

    def sheet(items):
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", lineterminator="\n")
        w.writerow(
            (
                "draft_line",
                "role",
                "claim",
                "source",
                "location",
                "start",
                "end",
                "quote",
            )
        )
        for c in items:
            for r in c["evidence"]:
                w.writerow(
                    (
                        c["line"],
                        c["role"],
                        c["claim"],
                        r["source"],
                        r["location"],
                        r["start"],
                        r["end"],
                        r["quote"],
                    )
                )
        return buf.getvalue()

    atomic_text(out / "introduction.md", "\n".join(prose).strip() + "\n")
    atomic_text(out / "claim-sources.tsv", sheet(claims))
    atomic_text(
        out / "related-work.tsv",
        sheet(c for c in claims if c["role"] in {"related", "gap"}),
    )
    atomic_text(
        out / "contributions.tsv",
        sheet(c for c in claims if c["role"] == "contribution"),
    )
    report = {
        "sections": sections,
        "missing_sections": [k for k in ROLES if k not in represented],
        "claims": claims,
        "review": issues,
        "source_notes": errors,
    }
    write(out / "manuscript-sources.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("materials", type=Path)
    p.add_argument("draft", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--own", action="append", default=[])
    p.add_argument("--bibliography", type=Path)
    p.add_argument("--language", choices=("zh", "en"), default="zh")
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    try:
        bib = read(a.bibliography) if a.bibliography else {}
        if not isinstance(bib, dict) or not all(
            isinstance(v, str) for v in bib.values()
        ):
            raise ValueError("Bibliography maps source filenames to reference strings.")
        report = compile_draft(a.materials, a.draft, a.output, a.own, bib, a.language)
    except (ValueError, OSError) as exc:
        p.exit(2, f"{exc}\n")
    print(
        f"{len(report['claims'])} sourced claims, {len(report['review'])} lines for review"
    )
    if a.strict and (
        report["review"] or report["missing_sections"] or report["source_notes"]
    ):
        raise SystemExit(1)
