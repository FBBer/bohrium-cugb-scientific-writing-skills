"""Index the supplied research and assemble an editable introduction from the agent's source-backed draft."""
import difflib
import json
import re
import sys
from pathlib import Path
import subprocess

sys.path.insert(0,str(Path(__file__).resolve().parent/"scripts"))
from case_output import arguments,context,finish
from casework import atomic_text, read, write
from evidence_draft import source_index,render

def compare_draft(source,manuscript,out):
    old=source.splitlines(keepends=True)
    new=manuscript.splitlines(keepends=True)
    delta="".join(difflib.unified_diff(old,new,fromfile="supplied draft",tofile="revised introduction"))
    atomic_text(out/"changes.diff",delta)
    return "changes.diff"

def main():
    parser=arguments(__doc__)
    parser.add_argument("--plan",type=Path,help="source-backed draft created from this case")
    parser.add_argument("--original",help="relative path to a supplied plain-text draft, for the revision record")
    parser.add_argument("--word",action="store_true",help="also typeset Word and render a PDF")
    args=parser.parse_args()
    root,work,out,case,task=context(args)
    rows=source_index(root,work)
    write(work/"passages.json",rows)
    index=read(work/"sources.json")
    issues=list(index["issues"])
    plan_path=args.plan or work/"draft.json"
    if not plan_path.is_file():
        groups={}
        for row in rows:
            groups.setdefault(row["source"],[]).append({"loc":row["location"],"source_id":row["id"],"text":row["text"]})
        write(work/"source-cards.json",groups)
        write(work/"assignment.json",{"case_id":case["case_id"],"task":task,"contract":case.get("output_contract",{}),"files":list(groups)})
        # The first pass exposes material to the writing agent and never mislabels source notes as a manuscript.
        reason="Read task.md and source-cards.json, compose draft.json as in SKILL.md, and run again."
        print(reason)
        if not rows:issues.append({"reason":"No readable source passage was supplied"})
        if not (out/"result.json").exists():
            finish(case,{"main_result":{"materials":list(groups)},"sources":list(groups),"evidence":[],"status":"partial",
                         "uncertainty":issues+[{"reason":reason}],"artifacts":[]},
                         ["main_result","sources","status","uncertainty"],None,work,out)
        return 0
    plan=read(plan_path)
    report=render(plan,rows,out)
    manuscript=(out/"introduction.md").read_text(encoding="utf-8")
    issues+=report["review"]+report["bibliography_review"]
    if not report["claims"]:issues.append({"reason":"No supported manuscript sentences"})
    requested=plan.get("required_roles",["background","comparison","gap","contribution"])
    roles={item["role"] for item in report["claims"]}
    missing=[r for r in requested if r not in roles and not (r=="comparison" and "related" in roles)]
    if missing:issues.append({"reason":"No supported passage for these requested parts","parts":missing})
    issues+=plan.get("uncertainty",[])
    artifacts=["introduction.md","claims.json","comparisons.json"]
    if args.original:
        original=(root/args.original).resolve()
        if root not in original.parents or original.suffix.lower() not in {".md",".txt"} or not original.is_file():
            parser.error("--original must name a supplied plain-text manuscript")
        artifacts.append(compare_draft(original.read_text(encoding="utf-8-sig"),manuscript,out))
    if args.word or re.search(r"\bdocx\b|editable word|可编辑.{0,4}Word",task,re.I):
        try:
            from word_layout import new_document,save_document,preview_pdf
            doc=new_document(plan.get("title",""))
            for para in manuscript.strip().split("\n\n"):
                if para.startswith("## "):doc.add_heading(para[3:],level=1)
                elif para:doc.add_paragraph(para)
            target=out/"introduction.docx"
            save_document(doc,target)
            artifacts.append(target.name)
            preview_pdf(target,plan.get("language")=="zh")
            artifacts.append(target.with_suffix(".pdf").name)
        except (ImportError,OSError,ValueError,subprocess.SubprocessError) as exc:
            issues.append({"reason":str(exc)})
    refs=[a for claim in report["claims"] for a in claim["evidence"]]
    main_result={"manuscript":manuscript,"claims":report["claims"],"references":report["bibliography"]}
    comparisons=read(out/"comparisons.json")
    data={**main_result,"introduction":manuscript,"main_result":main_result,"evidence":refs,"sources":refs,
          "comparisons":comparisons,"uncertainty":issues,"status":"partial" if issues else "success",
          "artifacts":artifacts,"change_records":report["review"]+(["changes.diff"] if args.original else [])}
    write(work/"draft-result.json",data)
    return finish(case,data,["main_result","evidence","uncertainty","status","artifacts"],args.fields,work,out)

if __name__=="__main__":
    raise SystemExit(main())
