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
from graph import export
s="The aperture mask was used for the glare test on the bench."
idx=setup({"paper.txt":s});ev=evidence(idx,s)
plan={"nodes":[{"key":"m","type":"method","label":"aperture mask","scope":"optics","document":"paper.txt","evidence":[ev]},{"key":"t","type":"task","label":"glare test","scope":"optics","document":"paper.txt","evidence":[ev]}],
      "edges":[{"source":"m","target":"t","predicate":"used_for","scope":"bench","polarity":"positive","strength":"direct","evidence":[ev]}],
      "queries":[{"question":"Which task used a mask?","where":{"source":"m","predicate":"used_for"}},{"question":"Did the test implement the mask?","where":{"source":"t","target":"m"}},{"question":"Which tasks have direct evidence?","where":{"strength":"direct"},"target_type":"task"}]}
write(work/"graph-plan.json",plan);g,q=export(idx,plan,result);assert not g["issues"] and [len(x["edges"]) for x in q]==[1,0,1]
done({"graph":"graph.graphml","queries":q},[ev])
