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
from nanopubs import export
s="A shaded sensor recorded lower glare than an exposed sensor on the bench."
idx=setup({"paper.txt":s});ev=evidence(idx,s)
claim={"id":"c1","subject":"shaded sensor","predicate":"recorded less glare than","object":"exposed sensor","statement":s,"scope":"bench setup","polarity":"positive","evidence_type":"direct","evidence":[ev]}
record={"papers":{"paper.txt":{"title":"Synthetic bench note","hasVersion":"1"}},"claims":[claim]}
write(work/"claims.json",record);accepted,issues=export(idx,record,result)
assert len(accepted)==1 and not issues
assert (result/"nanopubs.trig").read_text().count("np:hasAssertion")==1
bad={**claim,"evidence":[{**ev,"quote":"invented phrase"}]}
assert export(idx,{"claims":[bad]},work/"rejected")[1]
done(accepted,[ev])
