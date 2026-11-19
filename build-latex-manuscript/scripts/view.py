"""Show the actual typeset page with editable source files."""
from pathlib import Path
from reader import bitmap, cli, data, details, esc, paragraph
TITLE = "LaTeX 排版成稿"

def page_image(source):
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            return ""
    with fitz.open(source) as doc:
        if not len(doc):
            return ""
        page = doc[0]
        blocks = [fitz.Rect(b[:4]) for b in page.get_text("blocks") if b[6] in (0,1)]
        box = page.rect
        # Trim uniform margins; retain every text, drawing and image on the first page.
        blocks += [d["rect"] for d in page.get_drawings() if not d["rect"].is_empty]
        if blocks:
            content = fitz.Rect(blocks[0])
            for b in blocks[1:]:
                content |= b
            box = (content + (-12,-12,12,12)) & page.rect
        pix = page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),clip=box,alpha=False)
        return '<figure>' + bitmap(pix.tobytes("png"),"image/png","编译稿第一页") + '</figure>'

def body(source):
    if not source.is_file():
        raise FileNotFoundError(source)
    content = page_image(source)
    folder = source.parent/"source"
    for path in sorted(folder.rglob("*.tex")) if folder.is_dir() else ():
        if path.is_file():
            content += details(str(path.relative_to(folder)), '<pre>' + esc(path.read_text(encoding="utf-8",errors="replace")) + '</pre>')
    return content

if __name__ == "__main__":
    cli(TITLE, body, link_label="打开完整 PDF")
