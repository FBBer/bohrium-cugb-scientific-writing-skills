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

from collections import defaultdict
records = json.loads((root / "references.json").read_text())
bykey={r["id"]:r for r in records}
if len(bykey)!=len(records): raise ValueError("Duplicate bibliography key")
draft=(root/"draft.md").read_text()
pattern=re.compile(r"\[((?:@[A-Za-z0-9_:-]+(?:\s*;\s*@[\w:-]+)*))\]")
cited=list(dict.fromkeys(k for m in pattern.finditer(draft) for k in re.findall(r"@([\w:-]+)",m[1])))
groups=defaultdict(list)
for k in cited:
    if k in bykey:
        r=bykey[k];groups[r["author"],str(r["year"])].append(r)
def suffix(i):
    letters=""
    while True:
        i,rem=divmod(i,26);letters=chr(97+rem)+letters
        if not i:return letters
        i-=1
labels={}
for (author,year),group in groups.items():
    for i,r in enumerate(sorted(group,key=lambda v:(v["title"].casefold(),v["id"]))):
        labels[r["id"]]=year+(suffix(i) if len(group)>1 else "")
def render(m):
    values=[]
    for key in re.findall(r"@([\w:-]+)",m[1]):
        values.append(bykey[key]["author"]+", "+labels[key] if key in labels else "@"+key)
    return "("+"; ".join(values)+")"
order=sorted(labels,key=lambda k:(bykey[k]["author"],labels[k],bykey[k]["title"]))
bibliography=[bykey[k]["author"]+" ("+labels[k]+"). "+bykey[k]["title"]+"." for k in order]
output("manuscript.md",pattern.sub(render,draft)+"\n\n## References\n\n"+"\n\n".join(bibliography)+"\n")
output("crosswalk.json",{"labels":labels,"unresolved":[k for k in cited if k not in bykey],"uncited":[k for k in bykey if k not in cited]})
