"""Answer an evidence-path question from an already exported graph."""

import argparse
import json
from pathlib import Path
from collections import defaultdict

from casework import read, write
from graph import query


def lookup(graph, spec):
    names = defaultdict(set)
    for node in graph["nodes"]:
        for key in [node["label"], *(m["key"] for m in node.get("members", []))]:
            names[key].add(node["id"])
    for endpoint in ("from", "to"):
        value = spec.get(endpoint)
        if len(names.get(value, ())) > 1:
            raise ValueError(f"ambiguous entity {value!r}: give its graph node ID")
    refs = {key: next(iter(ids)) for key, ids in names.items() if len(ids) == 1}
    return query(graph, spec, refs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph")
    parser.add_argument("question")
    parser.add_argument("--diagram", type=Path, help="write the matched paths as figures in this directory")
    args = parser.parse_args()
    try:
        graph = read(args.graph)
        result = lookup(graph, read(args.question))
        if args.diagram:
            from diagram import render
            output = render(graph, [result], args.diagram)
            write(args.diagram / "figures.json", output)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
