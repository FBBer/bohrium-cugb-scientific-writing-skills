"""Draw the directed evidence relations returned by a query as editable, print-sized SVG pages."""
import math
from pathlib import Path
import unicodedata
from xml.etree import ElementTree as ET
from casework import atomic_text

NS="http://www.w3.org/2000/svg"
ET.register_namespace("",NS)
FONT="Noto Sans CJK SC,Source Han Sans SC,PingFang SC,Microsoft YaHei,Arial,sans-serif"
COLORS={"method":"#dbeceb","task":"#e8eef9","metric":"#f9e9d6","data":"#e4eddb","finding":"#eee6f4","author":"#f4e6e3"}

def element(parent,tag,attrs):
    return ET.SubElement(parent,"{"+NS+"}"+tag,{k:str(v) for k,v in attrs.items()})
def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in {"F","W"} else 1 for c in s)
def wrap(s,n):
    text=str(s).replace("_"," ");lines=[]
    while width(text)>n:
        j=0
        while j<len(text) and width(text[:j+1])<=n:j+=1
        blank=text.rfind(" ",0,j+1)
        if blank>j//2:j=blank
        lines.append(text[:j].strip());text=text[j:].strip()
    return lines+[text]
def label(root,x,y,lines,*,size=16,anchor="middle",color="#243c49",bold=False):
    a=element(root,"text",{"x":x,"y":y,"font-size":size,"font-family":FONT,"text-anchor":anchor,"fill":color,"font-weight":600 if bold else 400})
    for i,s in enumerate(lines):
        t=element(a,"tspan",{"x":x,"dy":0 if i==0 else size*1.28});t.text=s
def render(graph,answers,out):
    nodes={n["id"]:n for n in graph["nodes"]};edges={e["id"]:e for e in graph["edges"]}
    groups=[(i,q["question"],[edges[x] for x in q["edges"]]) for i,q in enumerate(answers,1) if q["edges"]]
    if not groups and edges:groups=[(1,"Supported relations",list(edges.values()))]
    files=[];issues=[]
    for qid,question,rows in groups:
        for offset in range(0,len(rows),6):
            page=rows[offset:offset+6];title=wrap(question,76)
            y=28+len(title)*24;layouts=[]
            for e in page:
                source,target=nodes[e["source"]],nodes[e["target"]]
                a=wrap(source["label"],22);b=wrap(target["label"],22)
                relation=wrap(e.get("display_predicate") or e["predicate"],26)
                scope=wrap(e["scope"],27);notes=[]
                if e.get("polarity")!="positive":notes.append(e["polarity"])
                if e.get("strength")!="direct":notes.append(e["strength"])
                if notes:scope+=wrap(" · ".join(notes),27)
                height=max(85,29+max(len(a),len(b))*20,25+len(relation)*19+len(scope)*16)
                layouts.append((y,height,e,source,target,a,b,relation,scope));y+=height+14
            root=ET.Element("{"+NS+"}svg",{"width":"174mm","height":str(round(y/708*174,2))+"mm","viewBox":f"0 0 708 {y}","role":"img"})
            element(root,"title",{}).text=question
            element(root,"rect",{"width":708,"height":y,"fill":"white"})
            label(root,14,24,title,size=20,anchor="start",bold=True)
            for y0,h,e,src,tgt,a,b,rel,scope in layouts:
                center=y0+h/2
                g=element(root,"g",{"id":e["id"]})
                element(g,"title",{}).text=" | ".join([e["scope"]]+[r["quote"] for r in e["evidence"]])
                for x,n,lines in ((13,src,a),(495,tgt,b)):
                    box_h=max(48,len(lines)*20+16)
                    element(g,"rect",{"x":x,"y":center-box_h/2,"width":198,"height":box_h,"rx":6,"fill":COLORS.get(n["type"].casefold(),"#e8edf1"),"stroke":"#acbfc5","stroke-width":1})
                    label(g,x+99,center-(len(lines)-1)*10+5,lines,size=16,bold=True)
                attrs={"x1":215,"x2":485,"y1":center,"y2":center,"stroke":"#395967","stroke-width":2}
                if e["strength"]!="direct":attrs["stroke-dasharray"]="5 4"
                element(g,"line",attrs)
                element(g,"path",{"d":f"M 479 {center-5} L 491 {center} L 479 {center+5} Z","fill":"#395967"})
                label(g,352,center-8-(len(rel)-1)*18,rel,size=15)
                label(g,352,center+19,scope,size=13,color="#506a73")
            name=f"query-{qid:02d}-{offset//6+1:02d}"
            svg=Path(out)/(name+".svg");svg.parent.mkdir(parents=True,exist_ok=True)
            atomic_text(svg,ET.tostring(root,encoding="unicode"))
            files.append(svg.name)
            try:
                try:import pymupdf as fitz
                except ImportError:import fitz
                with fitz.open(stream=svg.read_bytes(),filetype="svg") as src:
                    with fitz.open(stream=src.convert_to_pdf(),filetype="pdf") as pdf:
                        pdf.save(str(svg.with_suffix(".pdf")))
                        pdf[0].get_pixmap(dpi=220,alpha=False).save(str(svg.with_suffix(".png")))
                files+= [svg.with_suffix(".pdf").name,svg.with_suffix(".png").name]
            except (ImportError,RuntimeError,OSError,ValueError) as exc:
                issues.append({"figure":svg.name,"reason":"render the editable SVG with the installed image renderer: "+str(exc)})
    return {"files":files,"issues":issues}
