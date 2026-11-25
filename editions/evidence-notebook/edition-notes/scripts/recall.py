"""Look up a topic, its local conditions, or a measurement from a named table."""

import argparse
import json
from pathlib import Path
import re
from casework import read
from notebook import sha_file
from paper_structure import folded
from study_tables import lookup


def aliases(notes):
    found = {}
    for note in notes:
        s = " ".join(note["quote"].split())
        for m in re.finditer(r"\(([A-Z][A-Z0-9]{1,11})\)", s):
            acronym = m[1]
            words = re.findall(r"[A-Za-z]+", s[: m.start()])[-len(acronym) :]
            if "".join(w[0] for w in words).upper() == acronym:
                found.setdefault(acronym.casefold(), set()).add(
                    " ".join(words).casefold()
                )
    return {k: next(iter(v)) for k, v in found.items() if len(v) == 1}


def search(folder, terms, paper=None, section=None, role=None):
    cards = read(folder / "reading-cards.json")
    index = read(folder / "work/sources.json")
    sources = {x["id"]: x for x in index["sources"]}
    if paper and paper not in cards:
        raise ValueError("Unknown paper: " + paper)
    results = []
    for name, card in cards.items():
        if paper and name != paper:
            continue
        items = {n["anchor"]: n for n in card["notes"]}
        known = aliases(card["notes"])
        for n in card["notes"]:
            if role and n["role"] != role:
                continue
            path = " › ".join(n["path"])
            conds = [items[k] for k in n.get("conditions", [])]
            if section and folded(section) not in folded(path):
                continue
            hay = folded(" ".join([n["quote"], path, *(x["quote"] for x in conds)]))

            def contains(term):
                def has(word):
                    if re.fullmatch(r"[+−-]?\d+(?:\.\d+)?", word):
                        return bool(
                            re.search(
                                r"(?<![0-9a-z.+−-])"
                                + re.escape(word)
                                + r"(?!\d|\.\d|[eE][+−-]?\d)",
                                hay,
                            )
                        )
                    if re.fullmatch(r"[a-z0-9]+", word):
                        return bool(
                            re.search(
                                r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])",
                                hay,
                            )
                        )
                    return word in hay

                q = folded(term)
                return has(q) or any(
                    (q == short and has(long)) or (q == long and has(short))
                    for short, long in known.items()
                )

            if not all(contains(x) for x in terms):
                continue
            for q in [n, *conds]:
                if sources[q["id"]]["text"][q["start"] : q["end"]] != q["quote"]:
                    raise ValueError("Notebook does not match its source index")
            results.append(
                {
                    "paper": name,
                    "section": path,
                    "role": n["role"],
                    "quote": n["quote"],
                    "id": n["id"],
                    "location": n["location"],
                    "start": n["start"],
                    "end": n["end"],
                    "anchor": n["anchor"],
                    "conditions": [
                        {
                            k: x[k]
                            for k in (
                                "id",
                                "location",
                                "start",
                                "end",
                                "quote",
                                "anchor",
                            )
                        }
                        for x in conds
                    ],
                }
            )
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("notebook", type=Path)
    modes = p.add_subparsers(dest="mode", required=True)
    s = modes.add_parser("search")
    s.add_argument("terms", nargs="+")
    s.add_argument("--paper")
    s.add_argument("--section")
    s.add_argument("--role")
    t = modes.add_parser("table")
    t.add_argument("file")
    t.add_argument("--where", action="append", default=[])
    t.add_argument("--field", required=True)
    for parser in (s, t):
        parser.add_argument(
            "--originals",
            type=Path,
            help="Require the same original paper or table edition",
        )
    args = p.parse_args()
    folder = args.notebook
    try:
        cards = read(folder / "reading-cards.json")
        if args.mode == "table":
            tables = read(folder / "tables.json")
            if args.file not in tables:
                raise ValueError("Unknown attached table: " + args.file)
            record = tables[args.file]
            pairs = {}
            for item in args.where:
                k, eq, v = item.partition("=")
                if not eq or not k or k in pairs:
                    raise ValueError("--where needs one Field=Value per distinct field")
                pairs[k] = v
            answer = lookup(record, pairs, args.field)
            originals = {args.file: record["source_sha256"]}
        else:
            answer = search(folder, args.terms, args.paper, args.section, args.role)
            originals = {
                file: card["source_sha256"]
                for file, card in cards.items()
                if not args.paper or file == args.paper
            }
        if args.originals:
            for name, expected in originals.items():
                if sha_file(args.originals / name) != expected:
                    raise ValueError("Source edition differs: " + name)
        print(json.dumps(answer, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        p.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
