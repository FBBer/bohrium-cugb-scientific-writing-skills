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
from pathlib import PurePosixPath
labels=defaultdict(list); references=[]; files=[]
command=re.compile(r"\\(input|include|label|ref|eqref|pageref|autoref)\s*\{([^{}]+)\}")
def scan(file,parents):
    file=file.resolve()
    if root not in file.parents or file in parents:raise ValueError("Invalid include chain: "+file.name)
    rel=file.relative_to(root).as_posix();files.append(rel)
    for n,line in enumerate(file.read_text().splitlines(),1):
        line=re.split(r"(?<!\\)%",line,maxsplit=1)[0]
        for match in command.finditer(line):
            op,key=match.groups();loc={"file":rel,"line":n}
            if op in ("input","include"):
                candidate=Path(key)
                if not candidate.suffix:candidate=candidate.with_suffix(".tex")
                target=root/candidate
                if not target.is_file():target=file.parent/candidate
                scan(target,parents|{file})
            elif op=="label":labels[key].append(loc)
            else:references.append({"key":key,"kind":op,**loc})
scan(root/"main.tex",set())
for r in references:
    found=labels.get(r["key"],[])
    r.update(status="resolved" if len(found)==1 else ("ambiguous" if found else "missing"),locations=found)
duplicates={k:v for k,v in labels.items() if len(v)>1}
output("references.json",{"files":files,"labels":dict(labels),"references":references,"duplicates":duplicates})
lines=["# 文稿中的交叉引用",""]
for r in references:
    targets=", ".join(x["file"]+":"+str(x["line"]) for x in r["locations"])
    lines.append("- "+r["key"]+" · "+r["file"]+":"+str(r["line"])+" · "+r["status"]+" "+targets)
output("references.md","\n".join(lines)+"\n")
