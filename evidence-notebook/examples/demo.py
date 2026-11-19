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
sections={"Measurement":"The detector was shaded before calibration.","Observation":"The detector recorded 4 mV in shade.","Limit":"Only the bench configuration was evaluated."}
idx=setup({"paper.md":"\n\n".join(k+"\n"+v for k,v in sections.items())})
roles=["method","finding","limitation"];rows=[]
for i,(title,s) in enumerate(sections.items()):
    rows.append({"title":title,"paragraphs":[[{"id":"N"+str(i+1),"role":roles[i],"text":s,"evidence":[evidence(idx,s)],"keywords":["detector",title]}]]})
plan={"sections":rows};write(work/"notes-plan.json",plan);report=render("notes",idx,plan,result)
assert not report["issues"] and list(read(result/"topic-index.json")["detector"])==["N1","N2","N3"]
from copy import deepcopy
wrong=deepcopy(plan);wrong["sections"][1]["paragraphs"][0][0]["text"]="The detector recorded 4 V in shade."
assert render("notes",idx,wrong,work/"bad")["issues"]
done({"notes":"notes.md","coverage":report["sections"]},[evidence(idx,s) for s in sections.values()])
