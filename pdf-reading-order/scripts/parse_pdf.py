"""Extract geometric lines, layout order, tables and OCR evidence from real PDF pages."""
import argparse
from collections import Counter, defaultdict
import csv
import io
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from casework import write, atomic_text


def band_order(lines, width):
    """Partition by a supported gutter, then place spanning lines between column bands."""
    if len(lines) < 4:
        return sorted(lines,key=lambda a:(a["bbox"][1],a["bbox"][0]))
    choices=[]
    for pct in range(31,71,2):
        cut=width*pct/100
        left=[a for a in lines if a["bbox"][2]<cut-2]
        right=[a for a in lines if a["bbox"][0]>cut+2]
        if min(len(left),len(right))<2:
            continue
        overlap=min(max(l["bbox"][3] for l in left),max(l["bbox"][3] for l in right))-max(min(l["bbox"][1] for l in left),min(l["bbox"][1] for l in right))
        if overlap<=0:
            continue
        cross=len(lines)-len(left)-len(right)
        gap=min(a["bbox"][0] for a in right)-max(a["bbox"][2] for a in left)
        choices.append(((min(len(left),len(right))-2*cross,gap,-abs(pct-50)),cut))
    sort=lambda rows:sorted(rows,key=lambda a:(round(a["bbox"][1],1),a["bbox"][0]))
    if not choices or max(choices)[0][0] < 0:
        return sort(lines)
    cut=max(choices)[1]
    cross=sort(a for a in lines if a["bbox"][0]<=cut+2 and a["bbox"][2]>=cut-2)
    pending=[a for a in lines if a not in cross]
    out=[]
    for divider in cross+[None]:
        stop=divider["bbox"][1] if divider else float("inf")
        band=[a for a in pending if (a["bbox"][1]+a["bbox"][3])/2<stop]
        pending=[a for a in pending if a not in band]
        for column,rows in enumerate(([a for a in band if a["bbox"][2]<cut],[a for a in band if a["bbox"][2]>=cut]),1):
            for a in sort(rows):
                a["column"]=column
                out.append(a)
        if divider:
            divider["column"]="span"
            out.append(divider)
    return out


def make_line(text, box, **extra):
    return {"text":text,"bbox":[round(float(v),2) for v in box],**extra}


def render_page(path,page_num,work,doc=None,region=None):
    dest=work/f"page-{page_num}.png"
    if doc is not None:
        doc[page_num-1].get_pixmap(dpi=220,alpha=False,clip=region).save(dest)
    elif shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm","-f",str(page_num),"-l",str(page_num),"-r","220","-png","-singlefile",str(path),str(dest.with_suffix(""))],capture_output=True,check=True,timeout=75)
    else:
        raise ValueError("page rendering is unavailable")
    return dest


def ocr(path,page_num,work,width,height,doc,language,region=None):
    if not shutil.which("tesseract"):
        raise ValueError("Tesseract is unavailable")
    img=render_page(path,page_num,work,doc,region)
    left,top=0,0
    if region is not None:
        left,top,right,bottom=region;width,height=right-left,bottom-top
    r=subprocess.run(["tesseract",str(img),"stdout","-l",language,"--psm","3","tsv"],capture_output=True,check=True,timeout=90)
    groups=defaultdict(list)
    sx=sy=1.0
    for word in csv.DictReader(io.StringIO(r.stdout.decode("utf-8")),delimiter="\t",quoting=csv.QUOTE_NONE):
        if word["level"]=="1":
            sx=width/max(1,int(word["width"]))
            sy=height/max(1,int(word["height"]))
        if word["level"]=="5" and word["text"].strip():
            groups[tuple(word[k] for k in ("block_num","par_num","line_num"))].append(word)
    results=[]
    for words in groups.values():
        box=[min(int(w["left"]) for w in words)*sx,min(int(w["top"]) for w in words)*sy,
             max(int(w["left"])+int(w["width"]) for w in words)*sx,max(int(w["top"])+int(w["height"]) for w in words)*sy]
        conf=min(float(w["conf"]) for w in words)
        box=[box[0]+left,box[1]+top,box[2]+left,box[3]+top]
        results.append(make_line(" ".join(w["text"] for w in words),box,method="ocr",min_word_conf=conf,needs_review=conf<75))
    return results


def mupdf_pages(doc):
    for page in doc:
        lines, images = [], []
        data=page.get_text("dict",flags=0)
        for block in data["blocks"]:
            for line in block.get("lines",[]):
                spans=[{"text":s["text"],"size":round(s["size"],2),"flags":s["flags"],"bbox":s["bbox"],"baseline":s["origin"][1]} for s in line["spans"]]
                value="".join(s["text"] for s in spans)
                if value.strip():
                    lines.append(make_line(value,line["bbox"],method="text",spans=spans))
        if hasattr(page,"get_image_info"):
            images=[list(i["bbox"]) for i in page.get_image_info()]
        tables=[]
        if hasattr(page,"find_tables"):
            try:
                for t in page.find_tables().tables:
                    library_rows=t.extract();geometry=[];changes=[]
                    for ri,row in enumerate(t.rows):
                        values=[]
                        for ci,cell in enumerate(row.cells):
                            raw=library_rows[ri][ci] if ri<len(library_rows) and ci<len(library_rows[ri]) else None
                            if cell is None:
                                values.append(None);continue
                            crop=page.get_textbox(cell).strip()
                            values.append(crop if crop else raw)
                            if crop and raw is not None and crop!=raw:
                                changes.append({"row":ri+1,"column":ci+1,"raw":raw,"box_text":crop,"bbox":list(cell)})
                        geometry.append(values)
                    tables.append({"bbox":list(t.bbox),"rows":geometry,"row_cells":[[list(c) if c else None for c in row.cells] for row in t.rows],
                                   "cells":[list(c) if c else None for c in t.cells],"alternate_extractions":changes})
            except (ValueError,RuntimeError,AttributeError) as exc:
                tables.append({"unresolved":str(exc)})
        yield page.rect.width,page.rect.height,lines,images,tables


def poppler_pages(path):
    proc=subprocess.run(["pdftotext","-bbox-layout",str(path),"-"],capture_output=True,check=True,timeout=120)
    root=ET.fromstring(proc.stdout)
    for page in root.findall(".//{*}page"):
        lines=[]
        for line in page.findall(".//{*}line"):
            value=" ".join("".join(w.itertext()) for w in line.findall("./{*}word"))
            if value.strip():
                lines.append(make_line(value,[line.attrib[k] for k in ("xMin","yMin","xMax","yMax")],method="poppler"))
        yield float(page.attrib["width"]),float(page.attrib["height"]),lines,[],[]


OBJECT=re.compile(r"(?:(?<![A-Za-z])(?P<en>fig(?:ure)?\.?|table)\s*|(?P<zh>[图表])\s*)(?P<num>[SA]?\d+(?:[.-]\d+)*[a-z]?|[IVX]+|[一二三四五六七八九十]+)(?![A-Za-z0-9])",re.I)
SECTION=re.compile(r"^(?P<num>\d+(?:\.\d+)*)(?:[.)、]|\s)\s*(?=[A-Za-z\u4e00-\u9fff])")
MENTION_VERB=re.compile(r"^\s*(?:所?[示见]|显示|展示|说明|给出|列出|汇总|中|表明|(?:shows?|illustrates?|presents?|summari[sz]es?|lists?|gives?|demonstrates?|displays?|was|is|reports?)\b)",re.I)

def role(line,normal):
    t=line["text"].strip()
    obj=OBJECT.match(t)
    if obj and not MENTION_VERB.match(t[obj.end():]): return "caption"
    if re.match(r"^(abstract|references|acknowledg(e)?ments|摘要|参考文献)\s*[:：]?$",t,re.I): return "heading"
    if SECTION.match(t) and len(t)<95: return "heading_candidate"
    if re.search(r"[=∑∫≥≤≈]",t) and re.search(r"\(\d+[a-z]?\)\s*$",t): return "numbered_equation"
    if any(s["size"]>normal*1.22 for s in line.get("spans",[])) and len(t)<160: return "heading_candidate"
    return "body"

def structure(pages,bookmarks):
    outline=[];objects={}
    for page in pages:
        for line in page["lines"]:
            t=line["text"].strip()
            anchor={"line":line["id"],"page":page["page"],"bbox":line["bbox"],"text":t}
            if line["role"] in {"heading","heading_candidate"}:
                section=SECTION.match(t)
                outline.append({**anchor,"basis":"numbering" if section else "named_section" if line["role"]=="heading" else "typography",
                                "number":section["num"] if section else None,"level":1+section["num"].count(".") if section else None})
            for m in OBJECT.finditer(t):
                tag=(m["en"] or m["zh"]).lower()
                kind="table" if tag.startswith("tab") or tag=="表" else "figure"
                key=(kind,m["num"].upper())
                item=objects.setdefault(key,{"kind":kind,"number":key[1],"captions":[],"mentions":[]})
                field="captions" if m.start()==0 and line["role"]=="caption" else "mentions"
                item[field].append({**anchor,"label":m[0]})
    for item in objects.values():
        item["first_mention"]=next(iter(item["mentions"]),None)
    return {"headings":outline,"pdf_bookmarks":bookmarks,"objects":list(objects.values())}


def run(path,dest,language):
    try:
        import pymupdf as fitz
    except ImportError:
        try: import fitz
        except ImportError: fitz=None
    doc=None
    try:
        if fitz is not None:
            doc=fitz.open(path)
            if doc.needs_pass: raise ValueError("encrypted PDF requires an authorized password")
            pages=mupdf_pages(doc)
        elif shutil.which("pdftotext"):
            pages=poppler_pages(path)
        else:
            raise ValueError("requires PyMuPDF or Poppler pdftotext")
        result={"file":path.name,"coordinate_system":"PDF points from top left; physical pages start at 1","pages":[],"issues":[],"status":"success"}
        margins=defaultdict(set)
        with tempfile.TemporaryDirectory() as temp:
            for n,(width,height,lines,images,tables) in enumerate(pages,1):
                regions=[]
                if not lines:
                    regions=[None]
                else:
                    for box in images:
                        x0,y0,x1,y1=box
                        if (x1-x0)*(y1-y0)<.18*width*height:continue
                        covered=[a for a in lines if x0<=(a["bbox"][0]+a["bbox"][2])/2<=x1 and y0<=(a["bbox"][1]+a["bbox"][3])/2<=y1]
                        if sum(len(a["text"]) for a in covered)<45:
                            regions.append(box)
                for region in regions:
                    try:
                        recovered=ocr(path,n,Path(temp),width,height,doc,language,region)
                        def duplicate(a):
                            return any(a["text"].strip().casefold()==b["text"].strip().casefold() and abs(a["bbox"][1]-b["bbox"][1])<9 for b in lines)
                        new=[a for a in recovered if not duplicate(a)]
                        lines.extend(new)
                        if not recovered:
                            result["issues"].append({"page":n,"bbox":region,"reason":"OCR returned no readable words; inspect rendered region"})
                    except (OSError,ValueError,subprocess.SubprocessError) as exc:
                        result["issues"].append({"page":n,"bbox":region,"reason":"OCR incomplete: "+str(exc)})
                sizes=[s["size"] for a in lines for s in a.get("spans",[])]
                normal=statistics.median(sizes) if sizes else 10
                for a in lines:
                    a["role"]=role(a,normal)
                    if a["bbox"][3]<height*.095 or a["bbox"][1]>height*.91:
                        identity=re.sub(r"\d+","#",a["text"].strip().casefold())
                        margins[(identity,"top" if a["bbox"][3]<height*.095 else "bottom")].add(n)
                result["pages"].append({"page":n,"size":[width,height],"lines":lines,"images":images,"tables":tables})
        text=[]
        for p in result["pages"]:
            height=p["size"][1]
            central=[]
            for a in p["lines"]:
                side="top" if a["bbox"][3]<height*.095 else "bottom" if a["bbox"][1]>height*.91 else ""
                identity=re.sub(r"\d+","#",a["text"].strip().casefold())
                if side and len(margins[(identity,side)])>=2:
                    a["role"]="running_"+side
                else:
                    central.append(a)
            ordered=band_order(central,p["size"][0])
            p["marginalia"]=[a for a in p["lines"] if a["role"].startswith("running_")]
            p["lines"]=ordered
            for i,a in enumerate(ordered,1):
                a["id"]=f'p{p["page"]}:l{i}'
                if a.get("needs_review"):
                    result["issues"].append({"anchor":a["id"],"reason":"low-confidence OCR; check page crop"})
                text.append("["+a["id"]+"] "+a["text"])
        bookmarks=[{"level":row[0],"text":row[1],"page":row[2]} for row in doc.get_toc() if row[2]>0] if doc else []
        result["structure"]=structure(result["pages"],bookmarks)
        if result["issues"]: result["status"]="partial"
        write(dest,result)
        atomic_text(dest.with_suffix(".txt"),"\n".join(text)+"\n")
        return result
    finally:
        if doc is not None: doc.close()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("pdf",type=Path);p.add_argument("json",type=Path);p.add_argument("--lang",default="eng")
    a=p.parse_args()
    try: run(a.pdf,a.json,a.lang)
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError,ET.ParseError) as exc:
        write(a.json,{"file":a.pdf.name,"status":"partial","pages":[],"issues":[{"reason":str(exc)}]})
        raise SystemExit(2)
