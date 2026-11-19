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
raw={"a.md":"Study A measured static glare in daylight.","b.md":"Study B measured static glare in dim light.","ours.md":"We designed a moving-target glare test."}
idx=setup(raw);ev=[evidence(idx,v) for v in raw.values()]
plan={"sections":[{"title":"Introduction","paragraphs":[[{"id":"I1","role":"comparison","text":"Studies A and B measured static glare under different illumination conditions.","evidence":ev[:2]},{"id":"I2","role":"gap","text":"Within these two studies, moving-target glare was not evaluated.","condition":"restricted to the supplied studies","status":"inference","reason":"Both excerpts explicitly specify static tests.","evidence":ev[:2]}],[{"id":"I3","role":"objective","text":"We designed a moving-target glare test.","evidence":ev[2:]}]]}],
      "comparisons":[{"work":name,"axis":"illumination","condition":value.split(" in ")[-1].rstrip("."),"evidence":[ev[i]]} for i,(name,value) in enumerate(list(raw.items())[:2])]}
write(work/"intro-plan.json",plan);r=render("introduction",idx,plan,result)
assert not r["issues"] and len(read(result/"comparison-matrix.json"))==2 and len(r["sources_used"])==3
done({"introduction":"introduction.md","comparison":"comparison-matrix.json"},ev,["Gap limited to the two supplied studies."])
