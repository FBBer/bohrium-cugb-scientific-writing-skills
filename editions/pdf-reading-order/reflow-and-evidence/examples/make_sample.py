"""Make a small two-column field note in the given empty directory. Requires PyMuPDF."""
import argparse
import json
from pathlib import Path
import pymupdf

def make(root):
    root.mkdir(parents=True,exist_ok=True)
    for name in ("case.json","task.md","field-note.pdf"):
        if (root/name).exists():raise FileExistsError(root/name)
    doc=pymupdf.open()
    page=doc.new_page(width=550,height=700)
    def line(x,y,text,size=11):page.insert_text((x,y),text,fontsize=size)
    line(44,83,"1. Nearshore depth",16)
    for x,words in [(44,["The west rod tilted.","A new reading followed."]),(307,["At the east rod the tide rose.","The inlet remained open."])]:
        for r,s in enumerate(words):line(x,140+22*r,s)
    line(44,250,"2. Instrument drift",16)
    line(44,517,"The field team repeated calibra-")
    line(275,670,"17")
    page=doc.new_page(width=550,height=700)
    line(44,85,"tion before the boat returned.")
    line(275,670,"18")
    doc.save(root/"field-note.pdf");doc.close()
    case={"case_id":"sample-shore","output_contract":{"required_fields":["case_id","paragraphs","evidence","status","uncertainty"]}}
    (root/"case.json").write_text(json.dumps(case))
    (root/"task.md").write_text("Recover both pages, including column and section order. Locate the calibration passage in the original PDF.")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("directory",type=Path);make(p.parse_args().directory)
