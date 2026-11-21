"""Write editable bilingual passages or Word revisions from the two aligned texts."""
from datetime import datetime, timezone
from difflib import SequenceMatcher
from itertools import count
from copy import deepcopy
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def save_document(doc, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".docx", delete=False) as temporary:
        name = temporary.name
    try:
        doc.save(name)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def new_document(title):
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    doc = Document()
    page = doc.sections[0]
    page.page_width, page.page_height = Cm(21), Cm(29.7)
    page.left_margin = page.right_margin = Cm(2.25)
    page.top_margin = page.bottom_margin = Cm(2.35)
    for key in ("Normal", "Title", "Heading 1"):
        style = doc.styles[key]
        style.font.name = "Liberation Serif"
        fonts = style.element.get_or_add_rPr().rFonts
        for attr in ("asciiTheme","hAnsiTheme","eastAsiaTheme","cstheme"):
            fonts.attrib.pop(qn("w:"+attr),None)
        fonts.set(qn("w:eastAsia"),"Noto Serif CJK SC")
        style.font.color.rgb = RGBColor(0,0,0)
        style.font.size = Pt(12 if key == "Normal" else 20 if key == "Title" else 14)
    settings = doc.styles["Title"].element.get_or_add_pPr()
    for border in settings.findall(qn("w:pBdr")):
        settings.remove(border)
    doc.core_properties.title = title
    doc.core_properties.author = ""
    if title:
        doc.add_paragraph(title, style="Title")
    return doc


def emit_change(paragraph, value, kind, serial, timestamp, formatting=None):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    if not value:
        return
    run = paragraph.add_run(value)._r
    if formatting is not None:
        run.insert(0,deepcopy(formatting))
    if kind == "equal":
        return
    span = OxmlElement("w:" + kind)
    span.set(qn("w:id"), str(next(serial)))
    span.set(qn("w:author"), "Manuscript revision")
    span.set(qn("w:date"), timestamp)
    if kind == "del":
        for atom in run.iter(qn("w:t")):
            atom.tag = qn("w:delText")
    paragraph._p.append(span)
    span.append(run)


def edit_offsets(old, new):
    tokens = lambda s: re.findall(r"[A-Za-zÀ-ž0-9]+(?:['’][A-Za-zÀ-ž]+)*|[ \t]+|[\s\S]", s)
    left, right = tokens(old), tokens(new)
    def positions(words):
        indices = [0]
        for word in words:
            indices.append(indices[-1]+len(word))
        return indices
    pos,after = positions(left),positions(right)
    for kind,a,b,c,d in SequenceMatcher(None,left,right,autojunk=False).get_opcodes():
        yield kind,pos[a],pos[b],after[c],after[d]


def tracked_paragraph(paragraph, old, new, serial, stamp):
    for tag,a,b,c,d in edit_offsets(old,new):
        if tag=="equal":
            emit_change(paragraph,old[a:b],"equal",serial,stamp)
        else:
            emit_change(paragraph,old[a:b],"del",serial,stamp)
            emit_change(paragraph,new[c:d],"ins",serial,stamp)


def revise_original(path, source, draft, dest, prefix):
    """Retain the whole supplied Word document and its unaffected parts, including original styles."""
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    outputs = [dest/(prefix+"revised.docx"),dest/(prefix+"tracked.docx")]
    if path.resolve() in {x.resolve() for x in outputs}:
        raise ValueError("choose an output directory separate from the input document")
    docs = [Document(path), Document(path)]
    pars = [list(doc.element.body.iter(qn("w:p"))) for doc in docs]
    older = [int(n.get(qn("w:id"),"0")) for n in docs[1].element.iter()
             if n.tag in {qn("w:ins"),qn("w:del")} and n.get(qn("w:id"),"").isdigit()]
    serial = count(max(older,default=0)+1)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plans = {item["id"]:item for item in source["segments"]}
    used = set()
    for row in draft:
        item = plans[row["id"]]
        old, new = item["text"], row["target"]
        if old == new:
            continue
        pos = re.fullmatch(r"word/document\.xml:p([1-9]\d*)",str(item.get("location","")))
        if not pos or int(pos[1]) > len(pars[0]) or int(pos[1]) in used:
            raise ValueError("changed segment needs its own Word paragraph anchor: "+str(item["id"]))
        used.add(int(pos[1]))
        pair = [Paragraph(nodes[int(pos[1])-1],doc) for nodes,doc in zip(pars,docs)]
        p = pair[0]
        unsupported = any(child.tag not in {qn("w:r"),qn("w:pPr")} for child in p._p)
        run_parts = {qn("w:rPr"),qn("w:t"),qn("w:tab"),qn("w:br"),qn("w:cr")}
        if unsupported or any(c.tag not in run_parts for run in p.runs for c in run._r) or p.text != old:
            raise ValueError("open this anchored paragraph in Word to preserve its fields, equations or source text: "+str(item["id"]))
        spans,offset=[],0
        for run in p.runs:
            if run.text:
                spans.append((offset,offset+len(run.text),run._r.rPr))
                offset+=len(run.text)
        for para in pair:
            for run in list(para.runs):
                para._p.remove(run._r)
        for tag,a,b,c,d in edit_offsets(old,new):
            for lo,hi,fmt in spans:
                if lo>=b or hi<=a:
                    continue
                piece = old[max(lo,a):min(hi,b)]
                if tag=="equal":
                    for para in pair:
                        emit_change(para,piece,"equal",serial,stamp,fmt)
                else:
                    emit_change(pair[1],piece,"del",serial,stamp,fmt)
            if tag in {"insert","replace"}:
                fmt = next((fmt for lo,hi,fmt in spans if lo<=a<hi),spans[-1][2] if spans else None)
                emit_change(pair[0],new[c:d],"equal",serial,stamp,fmt)
                emit_change(pair[1],new[c:d],"ins",serial,stamp,fmt)
    for doc, path in zip(docs,outputs):
        save_document(doc,path)


def export_word(mode, source, draft, dest, prefix="", original_docx=None):
    from docx.shared import Cm
    from docx.oxml import OxmlElement
    title = source.get("title", "")
    original = {r["id"]:r for r in source["segments"]}
    if [x.get("id") for x in draft] != [x["id"] for x in source["segments"]]:
        raise ValueError("Word export needs one aligned draft per source segment in reading order")
    if any(not isinstance(x.get("target"),str) or not x["target"].strip() for x in draft):
        raise ValueError("Word export needs a nonempty target in each aligned segment")
    if original_docx:
        if mode!="edit":
            raise ValueError("source-template editing applies to revision mode")
        return revise_original(Path(original_docx),source,draft,dest,prefix)
    if mode == "translate":
        doc = new_document(title)
        from docx.oxml.ns import qn
        table = doc.add_table(rows=1,cols=3)
        table.autofit = False
        widths = [Cm(2.5),Cm(7),Cm(7)]
        for col,width in zip(table.columns,widths):
            col.width = width
        borders = OxmlElement("w:tblBorders")
        for side in ("top","left","bottom","right","insideH","insideV"):
            line = OxmlElement("w:"+side)
            line.set(qn("w:val"),"single" if side in {"insideH","bottom"} else "nil")
            line.set(qn("w:sz"),"4");line.set(qn("w:color"),"000000");borders.append(line)
        table._tbl.tblPr.append(borders)
        headings = [source.get("location_label","位置"),*source.get("column_labels",["原文","译文"])]
        if len(headings)!=3:
            raise ValueError("supply two column labels for the original language and translation")
        for cell,width,label in zip(table.rows[0].cells,widths,headings):
            cell.width = width
            cell.paragraphs[0].add_run(label).bold = True
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for row in draft:
            item = original[row["id"]]
            location = str(item.get("location") or item["id"])
            for cell,width,text in zip(table.add_row().cells,widths,(location,item["text"],row["target"])):
                cell.width = width
                cell.paragraphs[0].add_run(text)
        save_document(doc,dest/(prefix+"bilingual.docx"))
    else:
        revised, changes = new_document(title), new_document(title)
        serial = count(1)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for row in draft:
            item = original[row["id"]]
            revised.add_paragraph(row["target"])
            tracked_paragraph(changes.add_paragraph(), item["text"], row["target"], serial, stamp)
        save_document(revised,dest/(prefix+"revised.docx"))
        save_document(changes,dest/(prefix+"tracked.docx"))


def preview_pdf(source, has_cjk):
    """Render the actual document with an isolated LibreOffice profile and an available CJK font."""
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        raise ValueError("PDF preview requires LibreOffice; the editable Word document has been saved")
    if not has_cjk:
        with zipfile.ZipFile(source) as archive:
            parts = [n for n in archive.namelist() if n.startswith("word/") and n.endswith(".xml") and "styles" not in n]
            has_cjk = any(re.search(r"[\u3400-\u9fff]",archive.read(n).decode("utf-8",errors="replace")) for n in parts)
    with tempfile.TemporaryDirectory(dir=source.parent) as temp:
        root = Path(temp).resolve()
        profile = root/"profile"
        if has_cjk:
            fonts = profile/"user/fonts"
            fonts.mkdir(parents=True)
            located = []
            if shutil.which("kpsewhich"):
                for face in ("FandolSong-Regular.otf","FandolSong-Bold.otf"):
                    r=subprocess.run(["kpsewhich",face],capture_output=True,text=True,timeout=8)
                    if r.returncode==0 and Path(r.stdout.strip()).is_file():
                        located.append(Path(r.stdout.strip()))
            if not located and shutil.which("fc-match"):
                r=subprocess.run(["fc-match","-f","%{file}","sans-serif:lang=zh"],capture_output=True,text=True,timeout=8)
                if r.returncode==0 and Path(r.stdout.strip()).is_file():
                    located.append(Path(r.stdout.strip()))
            for font in located:
                shutil.copyfile(font,fonts/font.name)
            if not located:
                try:
                    import pymupdf
                    buf=pymupdf.Font("china-s").buffer
                    ext="otf" if buf.startswith(b"OTTO") else "ttc" if buf.startswith(b"ttcf") else "ttf"
                    (fonts/("cjk."+ext)).write_bytes(buf)
                except (ImportError,RuntimeError):
                    pass
        run = subprocess.run([office,"-env:UserInstallation="+profile.as_uri(),"--headless",
                              "--convert-to","pdf","--outdir",str(root),str(source.resolve())],
                             capture_output=True,timeout=90)
        pdf = root/source.with_suffix(".pdf").name
        if run.returncode or not pdf.is_file():
            raise ValueError("LibreOffice could not render "+source.name)
        with pdf.open("rb") as content:
            if content.read(5)!=b"%PDF-":
                raise ValueError("LibreOffice produced an unreadable PDF for "+source.name)
        if has_cjk:
            try:
                import pymupdf
            except ImportError:
                pass
            else:
                # A PDF can contain CJK Unicode mappings yet paint blank glyphs. Inspect actual glyph ink.
                with pymupdf.open(pdf) as doc:
                    samples=0;visible=0
                    for page in doc:
                        if samples>=12:break
                        for block in page.get_text("rawdict")["blocks"]:
                            for line in block.get("lines",[]):
                                for span in line["spans"]:
                                    for char in span["chars"]:
                                        if samples>=12 or not re.search(r"[\u3400-\u9fff]",char["c"]):continue
                                        samples+=1
                                        area=pymupdf.Rect(char["bbox"])
                                        if not area.is_empty:
                                            pixels=page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=area,colorspace=pymupdf.csGRAY).samples
                                            visible+=sum(i<150 for i in pixels)>max(2,len(pixels)*.015)
                    if samples and not visible:
                        raise ValueError("CJK glyphs were blank in the rendered PDF; use a CJK font in LibreOffice")
        os.replace(pdf,source.with_suffix(".pdf"))
