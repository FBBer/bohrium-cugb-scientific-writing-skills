"""Collate consecutive source passages with one or more target-language sentences."""
import re
from collections import Counter
from sourcebook import compact, dump, h, html_page, html_table, link
from edition_io import main, require

SIGNS = [(r"\bat most\b|no more than|不超过|至多|<=", "≤"),
         (r"\bat least\b|no less than|不少于|至少|>=", "≥"),
         (r"\bless than\b|小于", "<"), (r"\bgreater than\b|大于", ">")]
def invariants(text):
    for pattern, symbol in SIGNS:
        text = re.sub(pattern, symbol, text, flags=re.I)
    return Counter(re.findall(r"\[[0-9,\s–-]+\]|[<>≤≥]=?|(?<![0-9.])[−-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[α-ωΑ-Ω]", text))

def render(sources, plan, out):
    """Make a continuous translation, a parallel edition and an editable Word table."""
    expected = []
    for section in plan["scope"]:
        rows = [r for r in sources.rows if r["source"] == section["source"]]
        locs = [r["loc"] for r in rows]
        require(locs, f"unreadable source {section['source']}")
        first = locs.index(section.get("first",locs[0]))
        last = locs.index(section.get("last",locs[-1]))
        require(first <= last, "reversed passage range")
        expected.extend(rows[first:last+1])
    keys = [(r["source"],r["loc"]) for r in expected]
    require(keys and len(keys)==len(set(keys)), "empty or overlapping source range")
    seen, groups, refs, checks = [], [], [], []
    for n, item in enumerate(plan["groups"],1):
        anchors=[]
        for source, loc in item["segments"]:
            idx = len(seen)
            require(idx < len(keys) and keys[idx] == (source,loc), f"group {n}: missing, repeated or transposed passage at {source} {loc}")
            row = expected[idx]
            anchors.append(sources.resolve(source,row["text"],loc))
            seen.append((source,loc))
        target = item["target"]
        require(anchors and isinstance(target,list) and target and all(isinstance(s,str) and s.strip() for s in target), "empty source or translation")
        en = " ".join(a["quote"] for a in anchors)
        zh = " ".join(target)
        tags=[]
        if invariants(en) != invariants(zh):
            tags.append("数量、比较符或引文标记有差异，需对照原句。")
        for term in plan.get("glossary",[]):
            if term.get("groups") is not None and n not in term["groups"]:
                continue
            if any(re.search(r"(?<![A-Za-z])"+re.escape(t)+r"(?![A-Za-z])", en,re.I) for t in term["forms"]) and term["target"] not in zh:
                tags.append("术语译名："+term["target"])
        refs.extend(anchors)
        checks.extend({"group":n,"issue":t} for t in tags)
        groups.append({"group":n,"source":anchors,"target":target,"issues":tags})
    require(len(seen)==len(keys),"untranslated passages remain at the end")
    title=plan["title"]
    body="<p>"+h(plan.get("intro",""))+"</p>" if plan.get("intro") else ""
    cells=[]
    for group in groups:
        left="".join("<p>"+h(a["quote"])+" "+link(a)+"</p>" for a in group["source"])
        right="".join("<p>"+h(s)+"</p>" for s in group["target"])
        cells.append((left,right))
    html_page(out/"parallel.html",title,body+html_table((plan.get("source_language","原文"),plan.get("target_language","译文")),cells),refs)
    (out/"translation.txt").write_text("\n\n".join("\n".join(g["target"]) for g in groups)+"\n",encoding="utf-8")
    try:
        from docx import Document
    except ImportError:
        doc_written=False
    else:
        from docx.shared import RGBColor
        doc=Document()
        doc.core_properties.author="GPT-6.2Astra"
        heading=doc.add_heading(title,0)
        for run in heading.runs:
            run.font.color.rgb=RGBColor.from_string("000000")
        grid=doc.add_table(rows=0,cols=2)
        grid.style="Table Grid"
        headings=grid.add_row().cells
        for cell,label in zip(headings,(plan.get("source_language","原文"),plan.get("target_language","译文"))):
            run=cell.paragraphs[0].add_run(label);run.bold=True
            run.font.color.rgb=RGBColor.from_string("000000")
        for g in groups:
            a,b=grid.add_row().cells
            a.text="\n".join(s["quote"]+"  ("+s["source"]+" · "+s["loc"]+")" for s in g["source"])
            b.text="\n".join(g["target"])
        for row in grid.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.color.rgb=RGBColor.from_string("000000")
        doc.save(out/"parallel.docx")
        doc_written=True
    dump(out/"alignment.json",{"title":title,"author":"GPT-6.2Astra","groups":groups,"glossary":plan.get("glossary",[]),"passages":len(seen),"word_export":doc_written,"review":checks})

if __name__=="__main__":
    main(render)
