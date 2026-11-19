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
from parse_pdf import run
def pdf_document():
    objects=[]
    def obj(value):
        objects.append(value.encode("ascii"));return len(objects)
    obj("<< /Type /Catalog /Pages 2 0 R >>")
    obj("<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>")
    obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for page in (1,2):
        stream=""
        for x,y,value in [(40,760,"Optics report"),(45,630,"Left first observation"),(310,630,"Right first comparison"),(45,600,"Left second observation"),(310,600,"Right second comparison")]:
            stream+=f"BT /F 10 Tf {x} {y} Td ({value}) Tj ET\n"
        obj(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F 3 0 R >> >> /Contents {2*page+3} 0 R >>")
        obj(f"<< /Length {len(stream)} >>\nstream\n{stream}endstream")
    data=b"%PDF-1.4\n";offsets=[0]
    for i,x in enumerate(objects,1):
        offsets.append(len(data));data+=f"{i} 0 obj\n".encode()+x+b"\nendobj\n"
    start=len(data);data+=f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for x in offsets[1:]:data+=f"{x:010d} 00000 n \n".encode()
    return data+f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
(inp/"columns.pdf").write_bytes(pdf_document())
report=run(inp/"columns.pdf",result/"layout.json","eng")
p=report["pages"][0];assert [r["text"] for r in p["lines"]]==["Left first observation","Left second observation","Right first comparison","Right second comparison"]
assert p["marginalia"][0]["text"]=="Optics report"
done({"pages":len(report["pages"]),"reading_order":[r["id"] for r in p["lines"]]},[{"page":1,"bbox":p["lines"][0]["bbox"]}])
