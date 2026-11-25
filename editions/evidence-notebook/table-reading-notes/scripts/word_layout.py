"""Typeset and render a source-linked Word manuscript."""
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
