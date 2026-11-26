"""Read the original PDFs, recover their structure, and return locatable passages."""
from pathlib import Path
import hashlib
import re
import sys
import subprocess
from xml.etree.ElementTree import ParseError

sys.path.insert(0,str(Path(__file__).resolve().parent/"scripts"))
from case_output import arguments,context,finish
from casework import write,atomic_text
from parse_pdf import run
from passages import lookup

def main():
    parser=arguments(__doc__)
    parser.add_argument("--pdf",action="append",help="relative path to one of the supplied PDFs")
    parser.add_argument("--lang",default="eng",help="installed Tesseract codes, e.g. chi_sim+eng")
    parser.add_argument("--find",action="append",default=[],help="return literal source spans for a requested passage")
    args=parser.parse_args()
    root,work,out,case,task=context(args)
    if args.pdf:
        files=[]
        for name in args.pdf:
            file=(root/name).resolve()
            if root not in file.parents or file.suffix.lower()!=".pdf" or not file.is_file():
                parser.error("--pdf must name a PDF in the supplied materials")
            if file not in files:files.append(file)
    else:
        files=sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower()==".pdf")
    documents=[]; paragraphs=[]; evidence=[]; tables=[];equations=[]; headings=[];figures=[]; issues=[]; hits=[]; joins=[]; folios=[]; body=[]
    for path in files:
        rel=path.relative_to(root).as_posix()
        key=hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]
        dest=out/"documents"/key/"layout.json"
        try:layout=run(path,dest,args.lang)
        except (ValueError,RuntimeError,ImportError,OSError,subprocess.SubprocessError,ParseError) as exc:
            issues.append({"file":rel,"reason":str(exc)})
            continue
        structure=layout["structure"]
        documents.append({"file":rel,"layout":dest.relative_to(out).as_posix(),"pages":len(layout["pages"]),"sha256":layout["source_sha256"]})
        issues.extend({"file":rel,**issue} for issue in layout["issues"])
        headings.extend({"file":rel,**item} for item in structure["headings"])
        figures.extend({"file":rel,**obj} for obj in structure["objects"] if obj["kind"]=="figure")
        joins.extend({"file":rel,**item} for item in structure["continued_tables"])
        for phrase in args.find:
            hits.append({"file":rel,"phrase":phrase,"matches":lookup(layout,phrase)})
        body.append("# "+rel)
        by_page={}
        for para in structure["paragraphs"]:
            by_page.setdefault(para["page"],[]).append(para)
            paragraphs.append({"file":rel,**para})
        for page in layout["pages"]:
            n=page["page"];folio=page["folio"]
            folios.append({"file":rel,**folio})
            body.append("## PDF p. "+str(n)+(f' · {folio["printed"]}' if folio["printed"] else ""))
            for para in by_page.get(n,[]):
                body.append(para["text"])
            for line in page["lines"]+page.get("marginalia",[]):
                record={"file":rel,"page":n,"printed":folio["printed"],"line":line["id"],"bbox":line["bbox"],
                        "role":line["role"],"text":line.get("display_text",line["text"]),"method":line.get("method")}
                evidence.append(record)
                if line["role"]=="numbered_equation":equations.append(record)
            for i,table in enumerate(page["tables"],1):
                tables.append({"file":rel,"page":n,"index":i,**table})
    if not files:issues.append({"reason":"No PDF in the supplied materials"})
    if documents and not paragraphs:issues.append({"reason":"No readable body text recovered; inspect the original pages"})
    status="partial" if issues else "success"
    text="\n\n".join(body)
    atomic_text(out/"document.md",text+"\n")
    write(out/"evidence.json",evidence)
    main_result={"documents":documents,"sections":headings,"paragraphs":paragraphs,"tables":tables,"continued_tables":joins,
                 "equations":equations,"figures":figures,"folios":folios,"passage_matches":hits}
    artifacts=["document.md","evidence.json"]+[d["layout"] for d in documents]
    data={**main_result,"main_result":main_result,"text":text,"evidence":evidence,"sources":evidence,
          "headings":headings,"reading_order":paragraphs,"status":status,"uncertainty":issues,"artifacts":artifacts}
    write(work/"extracted.json",data)
    return finish(case,data,["main_result","evidence","status","uncertainty","artifacts"],args.fields,work,out)

if __name__=="__main__":
    raise SystemExit(main())
