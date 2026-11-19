"""Self-contained synthetic example; pass a new local output directory."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from casework import atomic_text,prepare,read,write,validate
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()/"demo-output"
inp=out/"input"; work=out/"work"; result=out/"output"
for d in (inp,work,result):d.mkdir(parents=True,exist_ok=True)
case={"case_id":"synthetic-example","output_contract":{"required":["case_id","outcome","status","evidence","uncertainty"]}}
write(inp/"case.json",case)
def setup(files):
    for name,body in files.items():atomic_text(inp/name,body)
    return prepare(inp,work)
def evidence(idx,quote):
    row=next(r for r in idx["sources"] if quote in r["text"])
    return {"id":row["id"],"quote":quote}
def done(outcome,ev,uncertainty=(),status="success"):
    body={"case_id":case["case_id"],"outcome":outcome,"status":status,"evidence":ev,"uncertainty":list(uncertainty)}
    write(result/"result.json",body)
    errors=validate(case,read(result/"result.json"))
    if errors: raise SystemExit(str(errors))
    print("Example result:",result/"result.json")
from compose import render
from settings import collect
raw={"default.cfg":"window=20 ms","run.log":"run_id=R1; window=15 ms","protocol.txt":"The exposure window was applied before sampling."}
idx=setup(raw);ev=[evidence(idx,s) for s in raw.values()]
settings=collect(inp);assert "window" in settings["candidate_conflicts"];write(work/"settings.json",settings)
plan={"sections":[{"title":"Acquisition","paragraphs":[[{"id":"M1","role":"procedure","text":raw["protocol.txt"],"evidence":[ev[2]]},{"id":"M2","role":"parameter","text":"The effective window was 15 ms.","evidence":[ev[1]]}]]}],"parameters":[{"name":"window","scope":"R1","value":"15","unit":"ms","status":"conflict","evidence":ev[:2],"resolution":"R1 runtime overrides default."}],"reproduction":{"effective_run":"R1","random_seed":"unreported"}}
write(work/"methods-plan.json",plan);r=render("methods",idx,plan,result);assert not r["issues"]
done({"methods":"methods.md","parameters":"parameters.json","reproduction":"reproduction.json"},ev,["Random seed was not reported."])

from subprocess import run as run_view
run_view([sys.executable, str(ROOT / "scripts/view.py"), str(result / "methods.md"), str(result / "reading.html")], check=True)
