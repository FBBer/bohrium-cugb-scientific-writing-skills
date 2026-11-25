"""Publish a self-contained edition from source materials and an authored reading plan."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from sourcebook import Sources, dump

def main(render):
    parser = argparse.ArgumentParser(description=render.__doc__)
    parser.add_argument("sources", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not args.sources.is_dir():
        parser.error("missing materials directory")
    spec = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=args.output) as scratch:
            work = Path(scratch)
            render(Sources(args.sources), spec, work)
            for product in sorted(work.iterdir()):
                os.replace(product, args.output / product.name)
    except (ValueError, KeyError, OSError, TypeError) as err:
        parser.exit(2, f"{args.plan.name}: {err}\n")

def anchor(sources, row):
    return sources.resolve(row["source"], row["quote"], row.get("loc", ""))

def require(value, message):
    if not value:
        raise ValueError(message)
    return value
