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
raw=["The two sensors measures 5 mm.","Figure 2 do not support a causal interpretation."]
idx=setup({"draft.txt":"\n\n".join(raw)})
segments={"segments":[{"id":str(i),"location":r["location"],"text":r["text"]} for i,r in enumerate(idx["sources"],1)]}
draft=[{"id":"1","target":"The two sensors measure 5 mm.","type":"agreement","reason":"The plural subject requires measure."},{"id":"2","target":"Figure 2 does not support a causal interpretation.","type":"agreement","reason":"Figure is singular; the negative scope is retained."}]
write(work/"segments.json",segments);write(work/"edits.json",draft)
report,md=audit(segments,draft,"edit");assert not report["findings"],report
assert len(report["changes"])==2
write(result/"audit.json",report);atomic_text(result/"revised.md",md)
bad=[dict(draft[0],target=draft[0]["target"].replace("mm","cm")),draft[1]]
assert any(i["issue"]=="protected quantity" for i in audit(segments,bad,"edit")[0]["findings"])
done(draft,[evidence(idx,s) for s in raw])

from subprocess import run as run_view
run_view([sys.executable, str(ROOT / "scripts/view.py"), str(result / "revised.md"), str(result / "reading.html")], check=True)
