"""Identify folios and recover explicitly continued numeric rows when headers are omitted."""
import re
from open_tables import VALUE

FOLIO=re.compile(r"^(?:page\s+|p\.\s*)?([ivxlcdm]+|\d{1,5})(?:\s*(?:/|of)\s*\d+)?$",re.I)
def folio(page, embedded):
    values=[]
    for line in page["lines"]+page.get("marginalia",[]):
        box=line["bbox"];height=page["size"][1]
        if box[3]<height*.10 or box[1]>height*.88:
            m=FOLIO.fullmatch(line["text"].strip())
            if m:values.append({"label":m[1],"line":line["id"],"bbox":box})
    distinct={v["label"].casefold() for v in values}
    if len(distinct)==1:
        return {"physical":page["page"],"printed":values[0]["label"],"source":"visible folio","evidence":values,"pdf_label":embedded}
    return {"physical":page["page"],"printed":None,"source":"ambiguous" if values else "unmarked","evidence":values,"pdf_label":embedded}

def omitted_header(series,grid,cols,table,page_width,previous_width):
    if not series["data"] or len(series["header"])!=len(cols) or not grid:return False
    old=series["data"][-1]; old_boxes=old.get("cells",[])
    new_boxes=next((row for row in table.get("row_cells",[]) if all(i<len(row) and row[i] for i in cols)),[])
    if len(old_boxes)!=len(cols) or not all(old_boxes) or not new_boxes:return False
    for index,(a,i) in enumerate(zip(old_boxes,cols)):
        b=new_boxes[i]
        # Text-derived grids end at the longest content. The outer right edge is not a divider.
        edges=(0,2) if index+1<len(cols) else (0,)
        if max(abs(a[k]/previous_width-b[k]/page_width) for k in edges)>.029:return False
    prev_vals=old["values"]
    numeric=[i for i,v in enumerate(prev_vals) if v and VALUE.fullmatch(str(v).strip())]
    if not numeric:return False
    row=grid[0]
    return all(cols[i]<len(row) and row[cols[i]] is not None and VALUE.fullmatch(str(row[cols[i]]).strip()) for i in numeric)
