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

plan=json.loads((root/"plan.json").read_text())
parts=[]; trail=[]; withheld=[]; citations={}
for i,row in enumerate(plan,1):
    phase=row["role"]
    refs=row["evidence"]
    if phase not in ("background","comparison","gap","contribution"):raise ValueError("Unknown role")
    if not refs or (phase=="gap" and (not row.get("scope") or row["scope"] not in row["text"])):
        withheld.append({"row":i,"reason":"missing evidence or stated scope"});continue
    if phase=="gap" and re.search(r"no (?:research|study|studies) (?:has|have|exists)|从未有人|尚无任何研究",row["text"],re.I):
        withheld.append({"row":i,"reason":"universal gap"});continue
    labels=[];supports=[]
    for a in refs:
        f=(root/a["file"]).resolve()
        if root not in f.parents:raise ValueError("Source outside materials")
        seq=f.read_text().splitlines();line=int(a["line"])
        if not (1<=line<=len(seq) and a["quote"].strip() and a["quote"] in seq[line-1]):raise ValueError("Unlocated quotation")
        if phase=="contribution" and a.get("type")!="own":raise ValueError("Contribution requires evidence from this work")
        if a["file"] not in citations:citations[a["file"]]=len(citations)+1
        labels.append(str(citations[a["file"]]));supports.append(a)
    parts.append(row["text"]+" ["+", ".join(dict.fromkeys(labels))+"].")
    trail.append({"sentence":row["text"],"role":phase,"sources":supports})
output("introduction.md","\n\n".join(parts)+"\n\n## Sources\n\n"+"\n".join(f"[{n}] {name}" for name,n in citations.items())+"\n")
output("claim-map.json",{"included":trail,"withheld":withheld})
