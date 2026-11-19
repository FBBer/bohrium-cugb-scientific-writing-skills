"""Find potentially conflicting parameter statements across JSON, YAML, logs and CSV configurations."""
import argparse
from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import re
from casework import pointer,write

def collect(root):
    observations=defaultdict(list); issues=[]
    def add(name,value,path,loc):
        observations[name.casefold()].append({"name":name,"value":str(value),"file":path,"locator":loc})
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in {"case.json","task.md"}: continue
        ext=path.suffix.lower();rel=path.relative_to(root).as_posix()
        if ext not in {".json",".yml",".yaml",".csv",".tsv",".txt",".log",".cfg",".ini",".toml"}: continue
        try:
            raw=path.read_text(encoding="utf-8-sig")
            data=None
            if ext==".json": data=json.loads(raw)
            if ext in {".yml",".yaml"}:
                try:
                    import yaml
                    try: data=yaml.safe_load(raw)
                    except yaml.YAMLError as exc:
                        issues.append({"file":rel,"reason":"invalid YAML: "+str(exc)})
                        continue
                except ImportError: pass
            if data is not None:
                for loc,value in pointer(data):
                    key=loc.split("/")[-1];add(key,value,rel,loc)
            elif ext in {".csv",".tsv"}:
                for n,row in enumerate(csv.DictReader(io.StringIO(raw),delimiter="\t" if ext==".tsv" else ","),2):
                    if "name" in row and "value" in row: add(row["name"],row["value"],rel,"row "+str(n))
                    else:
                        for k,v in row.items():
                            if k and v: add(k,v,rel,"row "+str(n))
            else:
                for n,line in enumerate(raw.splitlines(),1):
                    for m in re.finditer(r"(?<![\w-])([A-Za-z_][\w.-]*)\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[-+.\w/%]+)",line):
                        add(m[1],m[2],rel,"L"+str(n))
        except (OSError,ValueError) as exc: issues.append({"file":rel,"reason":str(exc)})
    return {"observations":dict(observations),"candidate_conflicts":{k:v for k,v in observations.items() if len({x["value"] for x in v})>1},"issues":issues}
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("materials",type=Path);p.add_argument("out")
    a=p.parse_args();write(a.out,collect(a.materials))
