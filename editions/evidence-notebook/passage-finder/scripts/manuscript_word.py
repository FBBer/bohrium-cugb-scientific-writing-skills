"""Keep the manuscript editable and link its claims to the cited passages in the same file."""
from collections import defaultdict
from itertools import count
import re
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor

from word_layout import new_document, preview_pdf, save_document


def bookmark(paragraph, name, serial):
    opening, closing = OxmlElement("w:bookmarkStart"), OxmlElement("w:bookmarkEnd")
    opening.set(qn("w:id"), str(serial))
    opening.set(qn("w:name"), name)
    closing.set(qn("w:id"), str(serial))
    paragraph._p.insert(1 if paragraph._p.pPr is not None else 0, opening)
    paragraph._p.append(closing)


def reference(paragraph, number, anchor):
    link = OxmlElement("w:hyperlink")
    link.set(qn("w:anchor"), anchor)
    link.set(qn("w:history"), "1")
    run = paragraph.add_run(f"[{number}]")
    run.font.color.rgb = RGBColor(0,0,0)
    run.underline = True
    link.append(run._r)
    paragraph._p.append(link)


def table_location(location):
    cell = re.fullmatch(r"(.*?)(?:R([1-9]\d*):C([1-9]\d*))", location)
    if cell:
        return cell[1], int(cell[2]), int(cell[3])
    cell = re.fullmatch(r"('(?:[^']|'')+'!)([A-Z]+)([1-9]\d*)(?::cached)?",location)
    if cell:
        col = 0
        for ch in cell[2]:
            col = col*26 + ord(ch)-ord("A")+1
        return cell[1], int(cell[3]), col
    return None


def evidence_table(doc, cells, number, serial, zh):
    columns = sorted({col for _,col in cells})
    rows = sorted({row for row,_ in cells})
    address_name = "原行" if zh else "Row"
    # A narrow two-column list remains readable for a very wide worksheet.
    if len(columns) > 6:
        table = doc.add_table(rows=0, cols=2)
        table.style = "Table Grid"
        for row in rows:
            for index,col in enumerate(c for c in columns if (row,c) in cells):
                address, value = cells[row,col]
                left,right = table.add_row().cells
                left.text,right.text = address,value
                if index==0:
                    bookmark(left.paragraphs[0], f"Passage_{number}_R{row}",next(serial))
        return
    table = doc.add_table(rows=1, cols=len(columns)+1)
    table.style = "Table Grid"
    for cell,label in zip(table.rows[0].cells,[address_name,*[f"C{c}" for c in columns]]):
        cell.paragraphs[0].add_run(label).bold = True
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row in rows:
        data = table.add_row().cells
        data[0].text = f"R{row}"
        bookmark(data[0].paragraphs[0], f"Passage_{number}_R{row}",next(serial))
        for dest,col in zip(data[1:],columns):
            if (row,col) in cells:
                dest.text = cells[row,col][1]


def export(mode, plan, sections, parameters, sources, path, preview):
    zh = str(plan.get("language","")).lower().startswith("zh")
    doc = new_document(plan.get("title", ""))
    passages = {}
    table_cells = defaultdict(dict)
    serial = count(1)

    def add_refs(paragraph, evidence):
        gathered = defaultdict(list)
        for item in evidence:
            source = sources[item["id"]]
            where, filename = source["location"],source["source"]
            cell = table_location(where)
            key = ("table",filename,cell[0]) if cell else ("text",filename,where,item["quote"])
            number = passages.setdefault(key, len(passages)+1)
            if cell:
                table_cells[key][cell[1],cell[2]] = where,source["text"]
            gathered[key].append((where,cell))
        for key,selection in gathered.items():
            number = passages[key]
            chosen_row = next((c[1] for _,c in selection if c and c[1]>1),None)
            anchor = f"Passage_{number}" + (f"_R{chosen_row}" if chosen_row is not None else "")
            reference(paragraph,number,anchor)

    for title, groups in sections:
        doc.add_heading(title, level=1)
        for group in groups:
            p = doc.add_paragraph()
            for idx,(text, evidence) in enumerate(group):
                p.add_run((" " if idx and not zh else "") + text)
                add_refs(p, evidence)
    if mode == "methods" and parameters:
        doc.add_heading("实验参数" if zh else "Experimental parameters", level=1)
        headings = ("参数", "数值", "单位", "作用对象", "来源") if zh else ("Parameter","Value","Unit","Scope","Source")
        table = doc.add_table(rows=1, cols=len(headings))
        table.style = "Table Grid"
        for cell, value in zip(table.rows[0].cells, headings):
            cell.paragraphs[0].add_run(value).bold = True
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for row in parameters:
            cells = table.add_row().cells
            scope = row.get("scope") or row.get("condition") or ""
            if isinstance(scope,dict):
                scope = ", ".join(f"{k}={v}" for k,v in scope.items())
            for cell, value in zip(cells,(row.get("name"),row.get("value"),row.get("unit"),scope)):
                cell.text = "—" if value is None else str(value)
            add_refs(cells[-1].paragraphs[0], row.get("evidence", []))
    if passages:
        doc.add_heading("引文出处" if zh else "Source passages", level=1)
        for key, number in passages.items():
            kind,file,where = key[:3]
            p = doc.add_paragraph()
            p.add_run(f"[{number}] {file}" + (" · "+where if where else "")).bold = True
            bookmark(p,f"Passage_{number}",next(serial))
            p.paragraph_format.keep_with_next = True
            if kind == "table":
                evidence_table(doc,table_cells[key],number,serial,zh)
            else:
                doc.add_paragraph(key[3])
    save_document(doc, path)
    if preview:
        preview_pdf(path,zh)
