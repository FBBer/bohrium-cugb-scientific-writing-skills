"""Assemble source-linked introduction paragraphs from the actual case materials."""
from pathlib import Path
from collections import defaultdict
import re
from casework import prepare, read, write, atomic_text
from comparisons import compare_evidence
from gaps import derive_gap

def source_index(folder, work):
    idx = prepare(folder, work)
    # Source material can also be embedded in case.json. Directions and file metadata are not evidence.
    return [r for r in idx["sources"] if r["source"] != "case.json" or
            re.search(r"(?:^|/)(?:materials?|papers?|literature|data|study|evidence|records|sources?|observations|experiment)(?:/|$)",r["location"],re.I)]

def resolve(ref, rows):
    quote=ref["quote"]
    if not isinstance(quote,str) or not quote.strip():
        raise ValueError("empty quotation")
    matches=[]
    for row in rows:
        if row["source"]!=ref["file"] or (ref.get("loc") and ref["loc"]!=row["location"]):
            continue
        for m in re.finditer(re.escape(quote),row["text"]):
            if "start" in ref and m.start()!=ref["start"]:
                continue
            matches.append({"file":row["source"],"loc":row["location"],"quote":m[0],
                            "source_id":row["id"],"start":m.start(),"end":m.end()})
    if len(matches)!=1:
        raise ValueError(f"{ref['file']}: {len(matches)} exact matches; specify loc or start")
    return matches[0]

def check_claim(role, claim, refs, plan):
    issues=[]
    if not refs:
        issues.append("missing source")
    if not claim.get("text","").strip():
        issues.append("missing text")
    return issues

def render(plan, rows, out):
    out.mkdir(parents=True,exist_ok=True)
    works=plan.get("works",{})
    citations, included, review, paragraphs, comparisons = {}, [], [], [], []
    for paragraph in plan["paragraphs"]:
        role=paragraph["role"]
        phrasing=[]
        for claim in paragraph["claims"]:
            try:
                refs=[resolve(a,rows) for a in claim["evidence"]]
                problems=check_claim(role,claim,refs,plan)
                gap=derive_gap(claim,refs,plan.get("own",[])) if role=="gap" else None
                comparison=compare_evidence(claim["comparison"],refs) if "comparison" in claim else None
            except (ValueError,KeyError,TypeError) as e:
                refs,problems=[],[str(e)]
            if problems:
                review.append({"role":role,"text":claim.get("text",""),"issues":problems})
                continue
            if comparison:
                comparisons.append({"sentence":claim["text"],**comparison})
            keys=[]
            for ref in refs:
                f=ref["file"]
                if f in plan.get("own",[]):continue
                citations.setdefault(f,len(citations)+1)
                keys.append(str(citations[f]))
            label=" ["+", ".join(dict.fromkeys(keys))+"]" if keys else ""
            text=claim["text"].strip(); stop=re.search(r"([。！？.!?]+)$",text)
            phrasing.append((text[:stop.start()]+label+stop[0]) if stop else text+label)
            included.append({"role":role,"text":text,"evidence":refs,**({"gap":gap} if gap else {})})
        if phrasing:
            paragraphs.append(("" if plan.get("language")=="zh" else " ").join(phrasing))
    manuscript="\n\n".join(paragraphs)
    if citations:
        heading="参考文献" if plan.get("language")=="zh" else "References"
        manuscript+="\n\n## "+heading+"\n\n"+"\n\n".join(
            f"[{i}] {works.get(f,f)}" for f,i in citations.items())
    report={"claims":included,"review":review,"files":dict(citations),"language":plan.get("language","")}
    atomic_text(out/"introduction.md",manuscript.strip()+"\n")
    write(out/"claims.json",report)
    write(out/"comparisons.json",comparisons)
    return report
