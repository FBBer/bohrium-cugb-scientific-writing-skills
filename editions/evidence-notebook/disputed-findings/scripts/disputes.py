"""Build section notes and compare independently sourced claims within explicitly matched conditions."""
from collections import defaultdict
from itertools import combinations
from edition_io import main,anchor,require
from sourcebook import dump,h,link,html_page,html_table
AXES=("material","condition","outcome","method")
def render(sources,spec,out):
    buckets=defaultdict(list);notes=[];refs=[];body=[];ids=set()
    for section in spec["sections"]:
        body.append("<h2>"+h(section["heading"])+"</h2>")
        for claim in section["claims"]:
            key=claim["id"];require(key and key not in ids,"duplicate claim");ids.add(key)
            direction=claim["direction"];require(direction in ("increases","decreases","unchanged","inconclusive"),"unknown finding")
            a=anchor(sources,claim["evidence"]);q=claim["question"];require(q.strip() and claim["note"].strip(),"missing conclusion")
            scope={s:claim["scope"].get(s,"").strip() for s in AXES}
            note=dict(id=key,section=section["heading"],question=q,scope=scope,direction=direction,note=claim["note"],evidence=a)
            notes.append(note);refs.append(a);buckets[q].append(note)
            body.append("<p>"+h(note["note"])+" "+link(a)+"</p>")
    pairs=[]
    for q,group in buckets.items():
        for x,y in combinations(group,2):
            if x["evidence"]["source"]==y["evidence"]["source"]:continue
            different=[s for s in AXES if x["scope"][s]!=y["scope"][s]]
            missing=[s for s in AXES if not x["scope"][s] or not y["scope"][s]]
            if missing:status="insufficient_scope"
            elif different:status="different_scope"
            elif "inconclusive" in (x["direction"],y["direction"]):status="inconclusive"
            elif x["direction"]==y["direction"]:status="agree"
            else:status="disagree"
            pairs.append(dict(question=q,claims=[x["id"],y["id"]],status=status,different=different,missing=missing))
    labels={"insufficient_scope":"可比条件交代不足","different_scope":"条件不同","inconclusive":"证据不足以定向","agree":"同条件、方向一致","disagree":"同条件、报告不同"}
    byid={n["id"]:n for n in notes}
    if pairs:
        body.append("<h2>跨文献比较</h2>"+html_table(("问题","两篇材料","判断","条件差异"),[(h(p["question"])," / ".join(link(byid[k]["evidence"]) for k in p["claims"]),h(labels[p["status"]]),h("、".join(p["different"]+p["missing"]))) for p in pairs]))
    html_page(out/"notebook.html",spec["title"],"".join(body),refs)
    dump(out/"notebook.json",dict(author="GPT-6.2Astra",notes=notes,comparisons=pairs))
    (out/"notes.md").write_text("\n\n".join("# "+spec["title"] if i==0 else v for i,v in enumerate([""]+[f'### {n["section"]}\n{n["note"]} [{n["evidence"]["source"]} · {n["evidence"]["loc"]}]' for n in notes]))+"\n",encoding="utf-8")
if __name__=="__main__":main(render)
