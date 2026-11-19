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
from prose import audit
sentences=["The optical gate did not drift at 10 ms [4].","Figure 2 shows the optical gate."]
idx=setup({"paper.txt":"\n\n".join(sentences)})
segments={"segments":[{"id":str(i),"location":r["location"],"text":r["text"]} for i,r in enumerate(idx["sources"],1)],"glossary":{"optical gate":"光学门"}}
draft=[{"id":"1","target":"在 10 ms 时，光学门未出现漂移 [4]。"},{"id":"2","target":"图 2 展示了光学门。"}]
write(work/"segments.json",segments);write(work/"translation.json",draft)
report,md=audit(segments,draft,"translate");assert not report["findings"],report
write(result/"audit.json",report);atomic_text(result/"bilingual.md",md)
bad=[dict(draft[0],target=draft[0]["target"].replace("10 ms","12 ms")),draft[1]]
assert any(i["issue"]=="protected quantity" for i in audit(segments,bad,"translate")[0]["findings"])
done(draft,[evidence(idx,s) for s in sentences])
