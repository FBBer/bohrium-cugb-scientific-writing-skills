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

from collections import Counter,defaultdict
import csv
with (root/"samples.csv").open(encoding="utf-8-sig",newline="") as stream:
    reader=csv.DictReader(stream)
    if not {"sample","group","split"}.issubset(reader.fieldnames or []):raise ValueError("Required columns: sample, group, split")
    rows=list(reader)
groups=defaultdict(set);samples=defaultdict(list);sizes=Counter();members=defaultdict(set)
for line,row in enumerate(rows,2):
    sample,group,split=(row[k].strip() for k in ("sample","group","split"))
    if not all((sample,group,split)):raise ValueError("Blank sample, group or split on line "+str(line))
    groups[group].add(split);samples[sample].append(line);sizes[split]+=1;members[split].add(group)
overlap={k:sorted(v) for k,v in groups.items() if len(v)>1}
duplicates={k:v for k,v in samples.items() if len(v)>1}
by_split={s:{"rows":sizes[s],"groups":len(members[s])} for s in sorted(sizes)}
sentences=[f"The manifest contains {len(rows)} rows, {len(samples)} distinct sample identifiers and {len(groups)} groups."]
sentences.extend(f"The {s} split contains {v['rows']} rows from {v['groups']} groups." for s,v in by_split.items())
if overlap:sentences.append("Groups appearing in multiple splits: "+", ".join(sorted(overlap))+". Group independence cannot be assumed.")
else:sentences.append("Each recorded group appears in a single split.")
if duplicates:sentences.append("Repeated sample identifiers: "+", ".join(sorted(duplicates))+".")
output("methods.md","## Experimental partition\n\n"+" ".join(sentences)+"\n")
output("split-evidence.json",{"by_split":by_split,"groups_in_multiple_splits":overlap,"repeated_ids_with_source_rows":duplicates})
