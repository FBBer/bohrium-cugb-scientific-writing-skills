"""Embed the actual cells from a paper's data table in its section notes."""
import csv
from decimal import Decimal,InvalidOperation
from functools import lru_cache
import re
from edition_io import main,anchor,require
from sourcebook import dump,h,html_page,html_table,link
NUM=r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
def interpret(s):
    raw=s.strip()
    if not raw or raw.casefold() in ("na","n/a","—","nd","not detected","n.d."):
        return {"type":"blank" if not raw else "reported_missing","raw":s}
    m=re.fullmatch(r"(<=|>=|[<>≤≥])\s*("+NUM+")",raw)
    if m:return {"type":"bound","comparison":m[1],"limit":m[2],"raw":s}
    m=re.fullmatch("("+NUM+r")\s*(?:±|\+/-)\s*("+NUM+")",raw)
    if m:return {"type":"with_uncertainty","value":m[1],"uncertainty":m[2],"raw":s}
    if re.fullmatch(NUM,raw):return {"type":"measured","value":raw,"raw":s}
    return {"type":"verbatim","raw":s}
def render(sources,plan,out):
    @lru_cache(maxsize=32)
    def load_table(file):
        path=(sources.root/file).resolve()
        require(path.is_relative_to(sources.root) and path.is_file(),"table missing")
        with path.open(encoding="utf-8-sig",newline="") as stream:
            reader=csv.DictReader(stream,delimiter="\t" if path.suffix.lower()==".tsv" else ",")
            fields=reader.fieldnames or []
            require(len(fields)==len(set(fields)),"duplicate table header")
            return fields,[(reader.line_num,row) for row in reader]
    body=[];refs=[];all_sections=[]
    for sec in plan["sections"]:
        body.append("<h2>"+h(sec["heading"])+"</h2>");notes=[]
        for v in sec["notes"]:
            a=anchor(sources,v["evidence"]);refs.append(a);cells=[];require(v["note"].strip(),"empty note")
            body.append("<p>"+h(v["note"])+" "+link(a)+"</p>")
            for c in v.get("cells",[]):
                fields,records=load_table(c["table"])
                require(c["column"] in fields and bool(c["where"]) and set(c["where"])<=set(fields),"unknown cell or empty row key")
                matched=[(num,row) for num,row in records if all(row[k]==val for k,val in c["where"].items())]
                require(len(matched)==1,"row selection must be unique: "+str(c["where"]))
                ln,row=matched[0]
                x=interpret(row[c["column"]]);x.update(table=c["table"],row=ln,column=c["column"],row_key=c["where"])
                if "unit_column" in c:
                    require(c["unit_column"] in fields,"missing unit column")
                    x["unit"]=row[c["unit_column"]]
                cells.append(x)
            kind={"measured":"观测值","bound":"界限","with_uncertainty":"读数与误差","blank":"空白","reported_missing":"原表缺测标记","verbatim":"原表文字"}
            if cells:body.append(html_table(("原表行","列","原值","单位","读法"),[(h(x["table"]+" · L"+str(x["row"])),h(x["column"]),h(x["raw"]) if x["raw"].strip() else "空白",h(x.get("unit","")),h(kind[x["type"]])) for x in cells]))
            notes.append(dict(note=v["note"],evidence=a,cells=cells))
        all_sections.append(dict(heading=sec["heading"],notes=notes))
    html_page(out/"notebook.html",plan["title"],"".join(body),refs)
    dump(out/"cells.json",dict(author="GPT-6.2Astra",sections=all_sections))
if __name__=="__main__":main(render)
