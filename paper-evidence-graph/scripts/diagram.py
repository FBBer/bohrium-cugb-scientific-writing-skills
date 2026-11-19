"""Draw the directed evidence relations returned by a query as editable, print-sized SVG pages."""
from pathlib import Path
import unicodedata
from xml.etree import ElementTree as ET
from casework import atomic_text

NS="http://www.w3.org/2000/svg"
ET.register_namespace("",NS)
FONT="Noto Sans CJK SC,Source Han Sans SC,PingFang SC,Microsoft YaHei,Arial,sans-serif"
INK="#000000"
ZH_QUALIFIERS={"negative":"否定", "uncertain":"不确定", "inference":"推断", "quoted":"转引"}
COLORS={
    "method":"#297b71", "task":"#536bac", "metric":"#ab601f",
    "data":"#678243", "finding":"#825a89", "author":"#ae5a4b",
}

def element(parent,tag,attrs):
    return ET.SubElement(parent,"{"+NS+"}"+tag,{k:str(v) for k,v in attrs.items()})
def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in {"F","W"} or c in "MW@%" else 1 for c in s)
def wrap(s,n):
    text=str(s).replace("_"," ");lines=[]
    while width(text)>n:
        j=0
        while j<len(text) and width(text[:j+1])<=n:j+=1
        blank=text.rfind(" ",0,j+1)
        if blank>j//2:j=blank
        lines.append(text[:j].strip());text=text[j:].strip()
    return lines+[text]
def label(root,x,y,lines,*,size=16,anchor="middle",bold=False):
    a=element(root,"text",{"x":x,"y":y,"font-size":size,"font-family":FONT,"text-anchor":anchor,"fill":INK,"font-weight":600 if bold else 400})
    for i,s in enumerate(lines):
        t=element(a,"tspan",{"x":x,"dy":0 if i==0 else size*1.28});t.text=s
def has_chinese(text):
    return any("\u3400" <= c <= "\u9fff" for c in text)


def export_print(svg, root, fitz):
    """Keep dashed connectors as native PDF strokes, including in the raster preview."""
    dashed = root.findall(".//{" + NS + "}line[@stroke-dasharray]")
    if dashed:
        # The SVG reader draws dash arrays as solid. Omit these lines during conversion.
        for line in dashed:
            line.set("stroke", "none")
        source = ET.tostring(root, encoding="utf-8")
    else:
        source = svg.read_bytes()
    with fitz.open(stream=source, filetype="svg") as vector:
        with fitz.open(stream=vector.convert_to_pdf(), filetype="pdf") as pdf:
            page = pdf[0]
            if dashed:
                _, _, width, height = map(float, root.get("viewBox").split())
                scale = min(page.rect.width / width, page.rect.height / height)
                x0 = (page.rect.width - width * scale) / 2
                y0 = (page.rect.height - height * scale) / 2
                for line in dashed:
                    start = (x0 + float(line.get("x1")) * scale, y0 + float(line.get("y1")) * scale)
                    end = (x0 + float(line.get("x2")) * scale, y0 + float(line.get("y2")) * scale)
                    pattern = " ".join(f"{float(length) * scale:.5f}" for length in line.get("stroke-dasharray").split())
                    page.draw_line(start, end, color=(0, 0, 0), width=float(line.get("stroke-width")) * scale,
                                   dashes=f"[{pattern}] 0", overlay=True)
            pdf.save(str(svg.with_suffix(".pdf")))
            page.get_pixmap(dpi=220, alpha=False).save(str(svg.with_suffix(".png")))


def render(graph,answers,out):
    nodes={n["id"]:n for n in graph["nodes"]};edges={e["id"]:e for e in graph["edges"]}
    groups=[(i,q["question"],[edges[x] for x in q["edges"]]) for i,q in enumerate(answers,1) if q["edges"]]
    if not groups and edges:
        caption="有原文依据的关系" if any(has_chinese(n["label"]) for n in nodes.values()) else "Supported relations"
        groups=[(1,caption,list(edges.values()))]
    files=[];issues=[]
    for qid,question,rows in groups:
        labels=ZH_QUALIFIERS if has_chinese(question) else {}
        for offset in range(0,len(rows),6):
            page=rows[offset:offset+6];title=wrap(question,54)
            y=24+len(title)*29;layouts=[]
            for e in page:
                source,target=nodes[e["source"]],nodes[e["target"]]
                a=wrap(source["label"],16);b=wrap(target["label"],16)
                relation=wrap(e.get("display_predicate") or e["predicate"],27)
                scope=wrap(e["scope"],30);notes=[]
                if e.get("polarity")!="positive":notes.append(labels.get(e["polarity"],e["polarity"]))
                if e.get("strength")!="direct":notes.append(labels.get(e["strength"],e["strength"]))
                if notes:scope+=wrap(" · ".join(notes),30)
                node_half=(max(len(a),len(b))-1)*12
                above=max(30,23+node_half,29+(len(relation)-1)*23)
                below=max(30,18+node_half,32+(len(scope)-1)*21)
                center=y+above
                layouts.append((center,e,source,target,a,b,relation,scope));y+=above+below+15
            root=ET.Element("{"+NS+"}svg",{"width":"174mm","height":str(round(y/708*174,2))+"mm","viewBox":f"0 0 708 {y}","role":"img"})
            element(root,"title",{}).text=question
            element(root,"rect",{"width":708,"height":y,"fill":"white"})
            label(root,12,27,title,size=23,anchor="start",bold=True)
            for center,e,src,tgt,a,b,rel,scope in layouts:
                g=element(root,"g",{"id":e["id"]})
                element(g,"title",{}).text=" | ".join([e["scope"]]+[r["quote"] for r in e["evidence"]])
                for x,n,lines in ((20,src,a),(516,tgt,b)):
                    marker=element(g,"circle",{"cx":x,"cy":center,"r":7,"fill":COLORS.get(n["type"].casefold(),"#687783")})
                    element(marker,"title",{}).text=n["type"]
                    label(g,x+16,center-(len(lines)-1)*12+6,lines,size=18,anchor="start",bold=True)
                attrs={"x1":208,"x2":488,"y1":center,"y2":center,"stroke":INK,"stroke-width":2}
                if e["strength"]!="direct":attrs["stroke-dasharray"]="5 4"
                element(g,"line",attrs)
                element(g,"path",{"d":f"M 482 {center-5} L 494 {center} L 482 {center+5} Z","fill":INK})
                label(g,350,center-10-(len(rel)-1)*23,rel,size=18)
                label(g,350,center+23,scope,size=16)
            name=f"query-{qid:02d}-{offset//6+1:02d}"
            svg=Path(out)/(name+".svg");svg.parent.mkdir(parents=True,exist_ok=True)
            atomic_text(svg,ET.tostring(root,encoding="unicode"))
            files.append(svg.name)
            try:
                try:import pymupdf as fitz
                except ImportError:import fitz
                export_print(svg,root,fitz)
                files+= [svg.with_suffix(".pdf").name,svg.with_suffix(".png").name]
            except (ImportError,RuntimeError,OSError,ValueError) as exc:
                issues.append({"figure":svg.name,"reason":"render the editable SVG with the installed image renderer: "+str(exc)})
    return {"files":files,"issues":issues}
