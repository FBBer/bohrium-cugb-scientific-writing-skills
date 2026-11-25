"""Resolve a reading note against the cited version and against the current version."""
from difflib import SequenceMatcher
from edition_io import main, require, anchor
from sourcebook import dump, h, html_page, link

def headings(rows):
    heading=""
    result={}
    for r in rows:
        if r["text"].startswith("#"):
            heading=r["text"].lstrip("# ").strip()
        result[r["loc"]]=heading
    return result

def render(sources, plan, out):
    """Publish an evidence-linked notebook while keeping changed evidence out of current claims."""
    body=[]; refs=[]; notes=[]; ids=set()
    for group in plan["sections"]:
        body.append("<h2>"+h(group["heading"])+"</h2>")
        for row in group["notes"]:
            key=row["id"]
            require(key and key not in ids,"duplicate note id "+key)
            ids.add(key)
            old=anchor(sources,row["before"])
            previous=[r for r in sources.rows if r["source"]==old["source"]]
            full=next(r["text"] for r in previous if r["loc"]==old["loc"])
            current_source=row.get("current_source",old["source"])
            current=[r for r in sources.rows if r["source"]==current_source]
            require(current,"missing current source "+current_source)
            old_heading=headings(previous)[old["loc"]]
            new_headings=headings(current)
            hits=[r for r in current if r["text"]==full and new_headings[r["loc"]]==old_heading]
            official=row.get("replacement")
            entry={"id":key,"section":group["heading"],"prior_note":row["note"],"before":old}
            refs.append(old)
            if official:
                after=anchor(sources,official["evidence"])
                require(after["source"]==current_source,"replacement belongs to a different document")
                require(official["note"].strip(),"replacement needs a new authored note")
                entry.update(status="revised",note=official["note"],current=after)
            elif len(hits)==1:
                after=sources.resolve(current_source,old["quote"],hits[0]["loc"])
                entry.update(status="located",note=row["note"],current=after)
            else:
                candidates=sorted(current,key=lambda r: SequenceMatcher(None,full,r["text"],autojunk=False).ratio(),reverse=True)
                entry.update(status="ambiguous" if len(hits)>1 else "changed",note=None,
                             candidates=[{"loc":r["loc"],"text":r["text"]} for r in (hits or candidates[:2])])
            notes.append(entry)
            if entry.get("current"):
                refs.append(entry["current"])
                body.append("<p>"+h(entry["note"])+" "+link(entry["current"])+"</p>")
                if entry["status"]=="revised":
                    body.append("<details><summary>上版记载</summary><p>"+h(row["note"])+" "+link(old)+"</p></details>")
            else:
                label="新稿有多处同文" if len(hits)>1 else "原段在新稿中有改动"
                body.append("<details open><summary>"+h(label)+"</summary><p>上版记载："+h(row["note"])+" "+link(old)+"</p>"+
                            "".join("<p>"+h(c["loc"])+"　"+h(c["text"])+"</p>" for c in entry["candidates"])+"</details>")
    require(notes,"no notes specified")
    html_page(out/"notebook.html",plan["title"],"".join(body),refs)
    dump(out/"notes.json",{"title":plan["title"],"author":"GPT-6.2Astra","notes":notes})
    md=["# "+plan["title"]]
    for group in plan["sections"]:
        md.append("## "+group["heading"])
        for row in [r for r in notes if r["section"]==group["heading"]]:
            if row["note"] is not None:
                a=row["current"];md.append(f"{row['note']} [{a['source']} · {a['loc']}]")
            else:
                md.append("上版记载待重读 — "+row["prior_note"]+"（"+row["before"]["source"]+"）")
    (out/"notebook.md").write_text("\n\n".join(md)+"\n",encoding="utf-8")

if __name__=="__main__":
    main(render)
