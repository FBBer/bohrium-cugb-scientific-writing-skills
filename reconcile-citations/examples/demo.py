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
from citations import reconcile
refs=[{"id":"A","title":"Synthetic optics A","DOI":"10.0000/demo-a"},{"id":"A-copy","title":"Synthetic optics A","DOI":"https://doi.org/10.0000/DEMO-A"},{"id":"B","title":"Synthetic optics B","DOI":"10.0000/demo-b"}]
raw="First [3]. Independently [1,2]. Equation $x[3]$."
write(inp/"records.json",refs);idx=setup({"draft.md":raw})
revised,report=reconcile(refs,raw)
assert revised=="First [1]. Independently [2]. Equation $x[3]$." and len(report["merge_decisions"])==1
atomic_text(result/"manuscript.md",revised);write(result/"citation-audit.json",report);write(result/"cited.csl.json",[r["record"] for r in report["cited"]])
done({"text":revised,"cited":report["cited"]},[evidence(idx,raw)],["Synthetic records are not externally verified."])
