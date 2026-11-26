"""Extract geometric lines, layout order, tables and OCR evidence from real PDF pages."""
import argparse
from collections import Counter, defaultdict
import csv
import io
from itertools import combinations
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from casework import write, atomic_text
from atlas import file_digest
from section_flow import section_breaks
from open_tables import borderless, table_tsv


def three_column_order(lines, width):
    """Require three recurring prose margins with simultaneous text and two empty gutters."""
    candidates = [line for line in lines if len(line["text"].strip()) >= 16
                  and .13 * width <= line["bbox"][2] - line["bbox"][0] <= .36 * width]
    clusters = []
    for line in sorted(candidates, key=lambda item: item["bbox"][0]):
        if not clusters or line["bbox"][0] - clusters[-1][0]["bbox"][0] > .018 * width:
            clusters.append([])
        clusters[-1].append(line)
    options = []
    for groups in combinations([group for group in clusters if len(group) >= 3], 3):
        starts = [min(line["bbox"][0] for line in group) for group in groups]
        if starts[0] > .23 * width or any(not .19 * width <= b-a <= .43 * width for a, b in zip(starts, starts[1:])):
            continue
        right = [max(line["bbox"][2] for line in group) for group in groups[:2]]
        gaps = [start - end for start, end in zip(starts[1:], right)]
        if min(gaps) < max(5, .013 * width):
            continue
        top = max(min(line["bbox"][1] for line in group) for group in groups)
        bottom = min(max(line["bbox"][3] for line in group) for group in groups)
        if bottom - top < 2 * statistics.median(line["bbox"][3] - line["bbox"][1] for group in groups for line in group):
            continue
        cuts = tuple((end + start) / 2 for end, start in zip(right, starts[1:]))
        options.append((sum(map(len, groups)), cuts))
    if not options:
        return None
    cuts = max(options)[1]
    dividers, columns = [], [[], [], []]
    for line in lines:
        left, _, right, _ = line["bbox"]
        crossed = sum(left < x < right for x in cuts)
        if crossed == 1:
            return None  # A partial-width float may change reading order in just two columns.
        if crossed == 2:
            dividers.append(line)
        else:
            columns[sum(left >= x for x in cuts)].append(line)
    order = lambda line: (line["bbox"][1], line["bbox"][0])
    result = []
    for divider in sorted(dividers, key=order) + [None]:
        stop = divider["bbox"][1] if divider else float("inf")
        for i, column in enumerate(columns):
            band = [line for line in column if (line["bbox"][1] + line["bbox"][3]) / 2 < stop]
            for line in sorted(band, key=order):
                line["column"] = i + 1
                result.append(line)
            columns[i] = [line for line in column if (line["bbox"][1] + line["bbox"][3]) / 2 >= stop]
        if divider:
            divider["column"] = "span"
            result.append(divider)
    return result


def band_order(lines, width, tables=()):
    """Partition by a supported gutter, then place spanning lines between column bands."""
    breaks = section_breaks(lines, width, tables)
    if breaks:
        output = []
        remaining = list(lines)
        for heading in breaks:
            y = heading["bbox"][1]
            band = [r for r in remaining if r is not heading and (r["bbox"][1]+r["bbox"][3])/2 < y]
            output.extend(band_order(band, width, tables))
            heading["column"] = "span"
            output.append(heading)
            used = {id(r) for r in band} | {id(heading)}
            remaining = [r for r in remaining if id(r) not in used]
        return output + band_order(remaining, width, tables)
    if len(lines) < 4:
        return sorted(lines,key=lambda a:(a["bbox"][1],a["bbox"][0]))
    if len(lines) >= 9 and not any("bbox" in table for table in tables):
        ordered = three_column_order(lines, width)
        if ordered is not None:
            return ordered
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


SUPERSCRIPT_DIGITS = str.maketrans("0123456789+-−", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻")

def readable_exponents(spans):
    """Use the PDF's own raised-digit flag and baseline; leave ambiguous typography intact."""
    normal = [s for s in spans if s["text"].strip() and not s["flags"] & 1]
    if not normal:
        return "".join(s["text"] for s in spans)
    largest = max(s["size"] for s in normal)
    baseline = statistics.median(s["baseline"] for s in normal if s["size"] >= largest*.9)
    fragments = []
    for s in spans:
        text = s["text"]
        if (s["flags"] & 1 and s["size"] < largest*.9 and baseline-s["baseline"] > largest*.15
                and re.fullmatch(r"\s*[+\-−]?\d+\s*", text)):
            text = text.translate(SUPERSCRIPT_DIGITS)
        fragments.append(text)
    return "".join(fragments)

NUMBER_IN_CELL = re.compile(r"[+\-−]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+\-]?\d+)?%?")

def lines_in_cell(lines, cell):
    if not cell:
        return []
    left, top, right, bottom = cell
    result = []
    for line in lines:
        x0, y0, x1, y1 = line["bbox"]
        if left <= (x0+x1)/2 < right and top <= (y0+y1)/2 < bottom:
            result.append(line)
    return sorted(result, key=lambda line: (line["bbox"][1], line["bbox"][0]))

def aligned_measurements(values, cells, lines, header_bounds, external_header):
    """Recover aligned measurements inside one ruled band; retain the source grid separately."""
    names = (values[0] or "").splitlines() if values else []
    if len(names) < 2 or not all(any(c.isalpha() for c in name) for name in names):
        return None
    candidates = []
    for col, value in enumerate(values[1:], 1):
        tokens = (value or "").splitlines()
        if len(tokens) == len(names) and all(NUMBER_IN_CELL.fullmatch(s.strip()) for s in tokens):
            candidates.append((col, tokens))
    if len(candidates) < 2:
        return None
    labels = lines_in_cell(lines, cells[0])
    if [r["text"].strip() for r in labels] != names:
        return None
    baseline = lambda r: r["spans"][0]["baseline"]
    tolerance = max(1.0, min(r["bbox"][3] - r["bbox"][1] for r in labels) * 0.2)
    if any(baseline(b) - baseline(a) <= 2*tolerance for a,b in zip(labels,labels[1:])):
        return None
    columns, numeric_lines = [], []
    for col, tokens in candidates:
        column_lines = lines_in_cell(lines, cells[col])
        if [r["text"].strip() for r in column_lines] != tokens:
            continue
        if any(abs(baseline(a)-baseline(b)) > tolerance for a,b in zip(labels,column_lines)):
            continue
        cell = cells[col]
        if external_header:
            heading = external_header["names"][col] if col < len(external_header["names"]) else None
        else:
            header = lines_in_cell(lines,(cell[0],header_bounds[1],cell[2],header_bounds[3]))
            heading = header[-1]["text"].strip() if header else None
        columns.append({"column":col+1,"heading":heading})
        numeric_lines.append(column_lines)
    if len(columns) < 2:
        return None
    records = []
    for index, name in enumerate(names):
        members = [column[index] for column in numeric_lines]
        boxes = [r["bbox"] for r in [labels[index], *members]]
        box = [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
        records.append({"label":name,"values":[r["text"].strip() for r in members],"bbox":box})
    return {"columns":columns,"records":records}


def mupdf_pages(doc):
    for page in doc:
        lines, images = [], []
        data=page.get_text("dict",flags=0)
        for block in data["blocks"]:
            for line_index,line in enumerate(block.get("lines",[])):
                spans=[{"text":s["text"],"size":round(s["size"],2),"flags":s["flags"],"bbox":s["bbox"],"baseline":s["origin"][1]} for s in line["spans"]]
                value="".join(s["text"] for s in spans)
                if value.strip():
                    row=make_line(value,line["bbox"],method="text",spans=spans,block=block.get("number"),block_line=line_index)
                    display=readable_exponents(spans)
                    if display!=value:
                        row["display_text"]=display
                    lines.append(row)
        if hasattr(page,"get_image_info"):
            images=[list(i["bbox"]) for i in page.get_image_info()]
        raised_lines=[line for line in lines if "display_text" in line]
        tables=[]
        if hasattr(page,"find_tables"):
            try:
                for t in page.find_tables().tables:
                    library_rows=t.extract();geometry=[];changes=[];formatted=[]
                    for ri,row in enumerate(t.rows):
                        values=[]
                        for ci,cell in enumerate(row.cells):
                            raw=library_rows[ri][ci] if ri<len(library_rows) and ci<len(library_rows[ri]) else None
                            if cell is None:
                                values.append(None);continue
                            crop=page.get_textbox(cell).strip()
                            value=crop if crop else raw
                            if value and raised_lines and lines_in_cell(raised_lines,cell):
                                replacements=defaultdict(set)
                                for part in lines_in_cell(lines,cell):
                                    replacements[part["text"].strip()].add(part.get("display_text",part["text"]).strip())
                                transformed=[]
                                for token in value.splitlines():
                                    variants=replacements.get(token.strip(),set())
                                    transformed.append(next(iter(variants)) if len(variants)==1 else token)
                                display="\n".join(transformed)
                                if display!=value:
                                    formatted.append({"row":ri+1,"column":ci+1,"raw":value,"display":display})
                                    value=display
                            values.append(value)
                            if crop and raw is not None and crop!=raw:
                                changes.append({"row":ri+1,"column":ci+1,"raw":raw,"box_text":crop,"bbox":list(cell)})
                        geometry.append(values)
                    content={"bbox":list(t.bbox),"rows":geometry,"row_cells":[[list(c) if c else None for c in row.cells] for row in t.rows],
                             "cells":[list(c) if c else None for c in t.cells],"alternate_extractions":changes}
                    # A hairline rule can be detected as an empty column between its two stroke edges.
                    raw_cells = content["row_cells"]
                    keep = []
                    for col in range(max(map(len,geometry),default=0)):
                        boxes = [row[col] for row in raw_cells if col < len(row) and row[col]]
                        empty = all(col>=len(row) or row[col] in (None,"") for row in geometry)
                        is_rule = len(boxes)==len(raw_cells) and all(0<b[2]-b[0]<=2.25 for b in boxes)
                        if not (empty and is_rule):
                            keep.append(col)
                    if keep and len(keep)<max(map(len,geometry),default=0):
                        content["reading_columns"] = [col+1 for col in keep]
                    if formatted:
                        content["formatted_cells"]=formatted
                    header=getattr(t,"header",None)
                    if header is not None and header.external:
                        content["external_header"]={"names":list(header.names),"bbox":list(header.bbox),
                                                    "cells":[list(cell) if cell else None for cell in header.cells]}
                    aligned=[]
                    for row_number,(values,cells) in enumerate(zip(geometry,content["row_cells"]),1):
                        if row_number==1 and not content.get("external_header"):
                            continue
                        band=aligned_measurements(values,cells,lines,t.rows[0].bbox,content.get("external_header"))
                        if band:
                            aligned.append({"grid_row":row_number,**band})
                    if aligned:
                        content["aligned_measurements"]=aligned
                    tables.append(content)
            except (ValueError,RuntimeError,AttributeError) as exc:
                tables.append({"unresolved":str(exc)})
        tables.extend(borderless(page.get_text("words"), tables))
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
MENTION_VERB=re.compile(r"^\s*(?:所?[示见]|显示|展示|说明|给出|列出|汇总|比较|对比|描绘|描绘了|绘制|表明|中|(?:shows?|compares?|contrasts?|depicts?|represents?|plots?|outlines?|contains?|illustrates?|presents?|summari[sz]es?|lists?|gives?|demonstrates?|displays?|was|is|reports?|provides?|identifies?|reveals?|indicates?)\b)",re.I)

def role(line,normal):
    t=line["text"].strip()
    obj=OBJECT.match(t)
    if obj and not MENTION_VERB.match(t[obj.end():]): return "caption"
    if re.match(r"^(abstract|references|acknowledg(e)?ments|摘要|参考文献)\s*[:：]?$",t,re.I): return "heading"
    if SECTION.match(t) and len(t)<95: return "heading_candidate"
    if re.search(r"[=∑∫≥≤≈]",t) and re.search(r"\(\d+[a-z]?\)\s*$",t): return "numbered_equation"
    if any(s["size"]>normal*1.22 for s in line.get("spans",[])) and len(t)<160: return "heading_candidate"
    return "body"

def object_regions(page,box,kind):
    width,height=page["size"]
    areas=page["images"] if kind=="figure" else [t["bbox"] for t in page["tables"] if "bbox" in t]
    candidates=[]
    for i,region in enumerate(areas,1):
        x0,y0,x1,y1=region
        if (x1-x0)*(y1-y0)>.88*width*height:continue
        overlap=max(0,min(box[2],x1)-max(box[0],x0))
        if overlap<.35*min(max(1,box[2]-box[0]),max(1,x1-x0)):continue
        gap=max(0,box[1]-y1,y0-box[3])
        if gap>min(85,.13*height):continue
        candidates.append({"page":page["page"],"index":i,"bbox":region,"distance_pt":round(gap,2)})
    candidates.sort(key=lambda r:r["distance_pt"])
    chosen=(candidates[0] if candidates and (len(candidates)==1 or candidates[1]["distance_pt"]-candidates[0]["distance_pt"]>=12) else None)
    return {"matched":chosen,"candidates":candidates,"basis":"caption geometry"}

CONTINUATION = re.compile(r"\b(?:continued|cont\.|cont[’']d)\b|\bcont\.|续表|接上表|[（(]续[）)]",re.I)


def continued_tables(pages, objects):
    """Link explicitly continued tables on adjacent pages; every cell row retains its physical origin."""
    by_page = {page["page"]:page for page in pages}
    linked = []
    for obj in objects:
        if obj["kind"] != "table":
            continue
        series = None
        for caption in sorted(obj["captions"], key=lambda c:(c["page"],c["bbox"][1])):
            match = caption.get("regions",{}).get("matched")
            if not match:
                continue
            page_number = caption["page"]
            tables = [table for table in by_page[page_number]["tables"] if "bbox" in table]
            table = tables[match["index"]-1]
            grid = table.get("rows") or []
            if not grid or not grid[0]:
                continue
            external = table.get("external_header") or {}
            cols = [i-1 for i in table.get("reading_columns",range(1,len(grid[0])+1))]
            grab = lambda row:[row[i] if i<len(row) else None for i in cols]
            header = grab(external.get("names") or grid[0])
            clean = lambda cells:tuple(" ".join(str(v or "").split()).casefold() for v in cells)
            continuing = bool(CONTINUATION.search(caption["text"]))
            carry = (series is not None and continuing and page_number == series["segments"][-1]["page"]+1)
            if carry:
                same_header = clean(header)==clean(series["header"])
                # A changed header or a different column count can describe a different panel.
                if not same_header or not any(clean(header)):
                    series = None
                    continue
            elif continuing:
                series = None
                continue
            else:
                series = {"number":obj["number"],"header":header,"segments":[],"data":[]}
            data_start = 0 if external else 1
            series["segments"].append({"page":page_number,"table":match["index"],"caption":caption["line"],"bbox":match["bbox"]})
            for row_number, values in enumerate(grid[data_start:],data_start+1):
                cells = table.get("row_cells",[])
                series["data"].append({"page":page_number,"table":match["index"],"row":row_number,"values":grab(values),
                                       "physical_columns":[i+1 for i in cols],"cells":grab(cells[row_number-1]) if row_number<=len(cells) else []})
            if len(series["segments"]) == 2:
                linked.append(series)
    return linked


def reading_paragraphs(pages):
    """Reassemble consecutive PDF lines from the same native paragraph, retaining physical line offsets."""
    records = []
    for page in pages:
        group, previous = None, None
        for line in page["lines"]:
            if line["role"].startswith("running_"):
                group,previous = None,None
                continue
            block = line.get("block")
            box = line["bbox"]
            previous_box = previous["bbox"] if previous else None
            same = (group is not None and block is not None and block==previous.get("block") and
                    line.get("block_line")==previous.get("block_line",-2)+1 and line["role"]==previous["role"] and
                    line["role"] in {"body","text","paragraph","caption"} and
                    box[1] >= previous_box[1]-1 and
                    box[1]-previous_box[3] <= 1.2*max(1,previous_box[3]-previous_box[1]) and
                    box[0] < previous_box[2] and box[2] > previous_box[0])
            if not same:
                group = {"page":page["page"],"role":line["role"],"text":"","spans":[]}
                records.append(group)
            value = line.get("display_text",line["text"])
            if same:
                left = group["text"][-1:]
                separator = "" if left in {"-","\u00ad","‐"} or (re.match(r"[\u3400-\u9fff]",left) and re.match(r"[\u3400-\u9fff]",value)) else " "
                group["text"] += separator
            start = len(group["text"])
            group["text"] += value
            group["spans"].append({"line":line["id"],"bbox":box,"start":start,"end":len(group["text"]),"method":line.get("method")})
            previous = line
    return records


def same_ocr_line(candidate, original):
    if candidate["text"].strip().casefold() != original["text"].strip().casefold():
        return False
    a,b = candidate["bbox"],original["bbox"]
    overlap = [max(0,min(a[i+2],b[i+2])-max(a[i],b[i])) for i in (0,1)]
    return all(overlap[i] >= 0.5*max(1,min(a[i+2]-a[i],b[i+2]-b[i])) for i in (0,1))


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
                found={**anchor,"label":m[0]}
                if field=="captions":found["regions"]=object_regions(page,line["bbox"],kind)
                item[field].append(found)
    for item in objects.values():
        item["first_mention"]=next(iter(item["mentions"]),None)
    return {"paragraphs":reading_paragraphs(pages),"headings":outline,"pdf_bookmarks":bookmarks,"objects":list(objects.values()),
            "continued_tables":continued_tables(pages,objects.values())}


def run(path,dest,language):
    try:
        import pymupdf as fitz
    except ImportError:
        try: import fitz
        except ImportError: fitz=None
    doc=None
    rotations=[]
    try:
        if fitz is not None:
            doc=fitz.open(path)
            if doc.needs_pass: raise ValueError("encrypted PDF requires an authorized password")
            for page in doc:
                rotations.append(page.rotation)
                if page.rotation:
                    page.set_rotation(0)
            pages=mupdf_pages(doc)
        elif shutil.which("pdftotext"):
            pages=poppler_pages(path)
        else:
            raise ValueError("requires PyMuPDF or Poppler pdftotext")
        result={"file":path.name,"source_sha256":file_digest(path),"coordinate_system":"PDF points from the top left of the unrotated page; physical pages start at 1","pages":[],"issues":[],"status":"success"}
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
                            return any(same_ocr_line(a,b) for b in lines)
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
                result["pages"].append({"page":n,"original_rotation":rotations[n-1] if rotations else None,"size":[width,height],"lines":lines,"images":images,"tables":tables})
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
            ordered=band_order(central,p["size"][0],p["tables"])
            p["marginalia"]=[a for a in p["lines"] if a["role"].startswith("running_")]
            for i,a in enumerate(p["marginalia"],1):a["id"]=f'p{p["page"]}:m{i}'
            p["lines"]=ordered
            for i,a in enumerate(ordered,1):
                a["id"]=f'p{p["page"]}:l{i}'
                if a.get("needs_review"):
                    result["issues"].append({"anchor":a["id"],"reason":"low-confidence OCR; check page crop"})
                text.append("["+a["id"]+"] "+a.get("display_text",a["text"]))
        bookmarks=[{"level":row[0],"text":row[1],"page":row[2]} for row in doc.get_toc() if row[2]>0] if doc else []
        result["structure"]=structure(result["pages"],bookmarks)
        if result["issues"]: result["status"]="partial"
        write(dest,result)
        atomic_text(dest.with_suffix(".tables.tsv"), table_tsv(result["pages"]))
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
