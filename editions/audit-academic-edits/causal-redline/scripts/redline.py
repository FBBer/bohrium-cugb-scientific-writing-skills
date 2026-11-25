from pathlib import Path
import argparse
import json
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("materials", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
root = args.materials.resolve()
out = args.destination.resolve()
out.mkdir(parents=True, exist_ok=True)

def output(name, value):
    (out / name).write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

import difflib
import html
original = (root / "draft.txt").read_text().splitlines()
proposed = json.loads((root / "edits.json").read_text())
edits = {int(item["line"]):item for item in proposed}
if len(edits) != len(proposed) or any(i<1 or i>len(original) for i in edits):
    raise ValueError("Each edit needs a unique source line")
number = re.compile(r"(?<!\w)[−+-]?\d+(?:[.,]\d+)?(?:\s*(?:%|mm|cm|kg|ms)\b|%)?")
cause = re.compile(r"\b(?:caus\w*|led to|resulted in|prevent\w*)\b|导致|引起",re.I)
hedge = re.compile(r"\b(?:may|might|possibly|suggest\w*|could)\b|可能|提示",re.I)
ledger, manuscript, markup = [], [], []
for i, before in enumerate(original, 1):
    item = edits.get(i)
    if item and item["original"]!=before:
        raise ValueError("Original text no longer matches line "+str(i))
    after = item["revision"] if item else before
    reasons = []
    if number.findall(before)!=number.findall(after): reasons.append("quantities")
    if cause.search(after) and not cause.search(before): reasons.append("causal_strength")
    if hedge.search(before) and not hedge.search(after): reasons.append("uncertainty")
    selected=before if reasons else after
    manuscript.append(selected)
    if item:
        ledger.append({"line":i,"original":before,"proposed":after,"retained":selected,"review":reasons})
        markup.append("<p>"+str(i)+". <del>"+html.escape(before)+"</del> <ins>"+html.escape(after)+"</ins> "+html.escape(", ".join(reasons))+"</p>")
output("manuscript.txt","\n".join(manuscript)+"\n")
output("decisions.json",ledger)
output("changes.html",'<!doctype html><meta charset="utf-8"><title>逐句修订</title><main><h1>逐句修订</h1>'+"".join(markup)+"</main>")
