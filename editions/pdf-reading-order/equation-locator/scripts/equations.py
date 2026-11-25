"""Find numbered displays and link references to the exact printed formula on its source page."""
import argparse
import base64
from collections import defaultdict
from pathlib import Path
import re
import pymupdf as fitz
from sourcebook import dump, h, html_page

TOKEN=r"(?:[A-Za-z](?:[.-])?)?\d+(?:[.-]\d+)*[a-z]?"
LABEL=re.compile(r"\s*[（(]\s*("+TOKEN+r")\s*[)）]\s*$")
CITE=re.compile(r"(?:\b(?:Eq(?:uation)?s?)\.?|公式|式)\s*[（(]\s*("+TOKEN+r")\s*[)）]",re.I)
MATH=re.compile(r"[=<>±∑∫≈≡→≤≥∝×÷∂√]")
def analyze(pdf,out):
    out.mkdir(parents=True,exist_ok=True)
    displays=defaultdict(list);mentions=[];notes=[]
    with fitz.open(pdf) as doc:
        for number,page in enumerate(doc,1):
            lines=[]
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines",[]):
                    s="".join(v["text"] for v in line["spans"]).strip()
                    if s:lines.append((s,fitz.Rect(line["bbox"])))
            if not lines:
                notes.append({"page":number,"reason":"无可读文字层"});continue
            for s,box in lines:
                mentions.extend({"key":m[1],"page":number,"quote":s,"box":list(box)} for m in CITE.finditer(s))
                tag=LABEL.search(s)
                if not tag or CITE.search(s):continue
                left=s[:tag.start()].strip()
                if left and not MATH.search(left):continue
                if not left and box.x0<page.rect.width*.46:continue
                parts=[(s,box)] if left else []
                if not left:
                    nearby=[(t,b) for t,b in lines if b.x1<=box.x0+2 and abs((b.y0+b.y1-box.y0-box.y1)/2)<=max(4,box.height*.55)]
                    eligible=[v for v in nearby if MATH.search(v[0])]
                    if not eligible:continue
                    start=min(v[1].x0 for v in eligible)
                    parts=sorted((v for v in nearby if v[1].x0>=start-2),key=lambda v:v[1].x0)
                clip=fitz.Rect(box)
                for _,rect in parts:clip|=rect
                clip=fitz.Rect(clip.x0-5,clip.y0-5,clip.x1+5,clip.y1+5)&page.rect
                key=tag[1];path=f"p{number}-eq-{key}-{len(displays[key])+1}.png"
                page.get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False).save(out/path)
                displays[key].append(dict(page=number,box=list(clip),image=path,text=" ".join(v[0] for v in parts)))
    body=[]
    for ref in mentions:
        hits=displays.get(ref["key"],[])
        ref.update(status="located" if len(hits)==1 else "ambiguous" if hits else "missing",targets=[x["image"] for x in hits])
        body.append("<p>"+h(ref["quote"])+"　· 第 "+str(ref["page"])+" 页</p>")
        if len(hits)==1:
            eq=hits[0];body.append('<p>式（'+h(ref["key"])+'） · 第 '+str(eq["page"])+' 页</p><img style="max-width:100%;height:auto" src="'+h(eq["image"])+'" alt="'+h(eq["text"])+'">')
        elif hits:body.append("<p>此编号对应多处公式，第 "+h("、".join(str(e["page"]) for e in hits))+" 页。</p>")
        else:body.append("<p>未找到这个编号的可读公式。</p>")
    if not mentions:body.append("<p>本文没有检出的显式公式引用。</p>")
    dump(out/"equations.json",dict(file=pdf.name,author="GPT-6.2Astra",displays=dict(displays),references=mentions,notes=notes))
    html_page(out/"equations.html",pdf.stem+" · 公式索引","".join(body))
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("pdf",type=Path);p.add_argument("out",type=Path);a=p.parse_args();analyze(a.pdf,a.out)
