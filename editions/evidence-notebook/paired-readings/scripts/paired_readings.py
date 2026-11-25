"""Create a section-aligned reading note and reconstruct within-unit contrasts from a data table."""
import csv
from decimal import Decimal, InvalidOperation
from edition_io import main, anchor, require
from sourcebook import dump, h, html_page, html_table, link, table

UNITS={"mm":("length","0.001"),"cm":("length","0.01"),"m":("length","1"),
       "ms":("time","0.001"),"s":("time","1"),"min":("time","60"),
       "mg":("mass","0.001"),"g":("mass","1"),"kg":("mass","1000"),
       "%":("percent","1"),"1":("ratio","1")}
def fmt(v):
    return format(v.normalize(),"f") if v else "0"

def summarize(sources,spec):
    name=spec["table"]
    file=(sources.root/name).resolve()
    require(file.is_relative_to(sources.root) and file.is_file(),"table missing")
    output_unit=spec["unit"];unit_dim,scale=UNITS.get(output_unit,(output_unit,"1"))
    left,right=spec["arms"];require(left!=right,"arms must be different")
    with file.open(encoding="utf-8-sig",newline="") as stream:
        rows=csv.DictReader(stream,delimiter="\t" if file.suffix==".tsv" else ",")
        cols=spec["columns"]; groups={}; warnings=[]
        criteria=spec.get("where",{})
        require(set(cols.values())|set(criteria) <= set(rows.fieldnames or []),"missing table columns")
        for row in rows:
            if any(row[k]!=v for k,v in criteria.items()) or row[cols["arm"]] not in (left,right):
                continue
            key=row[cols["pair"]].strip()
            require(key,"empty pairing identifier")
            arm=row[cols["arm"]];slot=groups.setdefault(key,{})
            require(arm not in slot,f"duplicate observation for {key}, {arm}")
            unit=row[cols["unit"]].strip()
            dim,factor=UNITS.get(unit,(unit,"1"))
            try:
                value=Decimal(row[cols["value"]])
                if dim!=unit_dim or not value.is_finite(): raise ValueError
                slot[arm]=(value*Decimal(factor)/Decimal(scale), rows.line_num)
            except (InvalidOperation,ValueError):
                slot[arm]=None
                warnings.append({"pair":key,"reason":"单位不可比或读数无效","source":f"{name} · L{rows.line_num}"})
    records=[]
    for key,slot in groups.items():
        if any(slot.get(a) is None for a in (left,right)):
            if set(slot)!={left,right}:
                warnings.append({"pair":key,"reason":"同一对象缺少一侧观测"})
            continue
        (v1,ln1),(v2,ln2)=slot[left],slot[right]
        diff=v2-v1
        records.append(dict(pair=key,left=fmt(v1),right=fmt(v2),difference=fmt(diff),
                            percent=fmt(100*diff/v1) if v1 else None,
                            evidence=[f"{name} · L{ln1}",f"{name} · L{ln2}"]))
    mean=fmt(sum((Decimal(r["difference"]) for r in records),Decimal(0))/len(records)) if records else None
    return dict(arms=[left,right],unit=output_unit,observed=len(groups),matched=len(records),mean_difference=mean,
                records=records,excluded=warnings,where=criteria)

def render(sources,plan,out):
    """Write the paper's claims alongside a transparent paired calculation."""
    refs=[];sections=[];body=[]
    for s in plan["sections"]:
        rows=[]
        body.append("<h2>"+h(s["heading"])+"</h2>")
        for c in s["claims"]:
            evidence=[anchor(sources,e) for e in c["evidence"]]
            require(c["text"].strip() and evidence,"each reading note needs a passage")
            refs.extend(evidence)
            rows.append({"text":c["text"],"evidence":evidence})
            body.append("<p>"+h(c["text"])+" "+" ".join(link(e) for e in evidence)+"</p>")
        sections.append({"heading":s["heading"],"claims":rows})
    calc=summarize(sources,plan["comparison"])
    arms=calc["arms"]; unit=calc["unit"]
    body.append("<h2>按同一对象配对</h2><p>"+h(f"{calc['observed']} 个对象中有 {calc['matched']} 个可配对。")+
                (h(f"平均差（{arms[1]} − {arms[0]}）为 {calc['mean_difference']} {unit}。") if calc["matched"] else "")+"</p>")
    body.append(html_table(("对象",arms[0]+" ("+unit+")", arms[1]+" ("+unit+")","差值","相对变化","出处"),
                [(h(r["pair"]),h(r["left"]),h(r["right"]),h(r["difference"]),"基数为零" if r["percent"] is None else h(r["percent"])+"%",h("；".join(r["evidence"]))) for r in calc["records"]]))
    if calc["excluded"]:
        body.append("<p>"+"；".join(h(r["pair"]+"："+r["reason"]) for r in calc["excluded"])+"。</p>")
    html_page(out/"notebook.html",plan["title"],"".join(body),refs)
    dump(out/"notes.json",{"title":plan["title"],"author":"GPT-6.2Astra","sections":sections,"comparison":calc})
    table(out/"pairs.tsv",("pair",*arms,"difference_"+unit,"relative_percent","source_rows"),
          [(r["pair"],r["left"],r["right"],r["difference"],r["percent"] if r["percent"] is not None else ""," | ".join(r["evidence"])) for r in calc["records"]])
if __name__=="__main__":
    main(render)
