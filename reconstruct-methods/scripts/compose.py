"""Render the author's evidence-mapped writing plan and audit each source quotation."""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal
import io
from pathlib import Path
import re
from casework import read, write, atomic_text, check_evidence

ROLES={
    "notes":{"question","data","method","finding","limitation","definition","context","interpretation"},
    "introduction":{"background","comparison","gap","objective","contribution","scope"},
    "methods":{"procedure","data","split","parameter","evaluation","baseline","environment","repetition","limitation"}}
NUMBER=re.compile(r"(?<![A-Za-z0-9_.])([+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?)(?:[ \t]*(%|‰|°C|°F|dBm|dB|[kMGTmunμµ]?(?:Hz|Pa|V|W|A|K|J|g|m|s|L|F|N|T|mol)(?:/[kmunμµ]?(?:s|m|L|g)(?:[²³23])?)?)(?![A-Za-z]))?")
def quantities(text):
    return [(Decimal(m[1].replace("−","-")),(m[2] or "").replace("µ","μ"),m[0].strip()) for m in NUMBER.finditer(text)]

def absent_measurements(sentence,source):
    known={(value,unit) for value,unit,_ in quantities(source)}
    return [raw for value,unit,raw in quantities(sentence) if (value,unit) not in known]

def tabular(header, rows):
    stream=io.StringIO()
    w=csv.writer(stream,delimiter="\t",lineterminator="\n")
    w.writerow(header);w.writerows(rows)
    return stream.getvalue()


def render(mode, index, plan, output):
    sources={r["id"]:r for r in index["sources"]}
    report={"mode":mode,"issues":[],"sections":[],"claims":0,"evidence_checks":0,"unresolved":[]}
    lookup=[]; paragraphs=[]; anchors={}; keywords=defaultdict(list); used=set(); ids=set()
    for section in plan["sections"]:
        title=section["title"]; paragraphs.append("## "+title); report["sections"].append(title)
        for group in section.get("paragraphs",[]):
            sentences=[]
            for row in group:
                key=row["id"]; kind=row["role"]; body=row["text"]
                if key in ids: report["issues"].append({"claim":key,"issue":"duplicate id"})
                ids.add(key);report["claims"]+=1
                if kind not in ROLES[mode]: report["issues"].append({"claim":key,"issue":"unknown role "+kind})
                ev=row.get("evidence",[]); state=row.get("status","supported")
                # A valid quotation may still be attributed to the wrong study or condition.
                for binding in row.get("bindings",[]):
                    ref={"id":binding.get("id"),"quote":binding.get("quote")}
                    if ref not in ev or check_evidence([ref],index["sources"]):
                        report["issues"].append({"claim":key,"issue":"unverified attribution anchor"});continue
                    pair=[binding.get("subject_in_source",""),binding.get("condition_in_source","")]
                    if any(not term or term.casefold() not in ref["quote"].casefold() for term in pair):
                        report["issues"].append({"claim":key,"issue":"subject and condition do not share the asserted source clause","terms":pair,"anchor":ref["id"]})
                if state in {"unreported","conflict","inference","uncertain"}:
                    report["unresolved"].append({"claim":key,"status":state,"reason":row.get("reason",""),"evidence":ev})
                    if not row.get("reason"): report["issues"].append({"claim":key,"issue":"explain uncertainty or inference"})
                if not ev and state not in {"unreported","uncertain"}: report["issues"].append({"claim":key,"issue":"missing evidence"})
                for err in check_evidence(ev,index["sources"]): report["issues"].append({"claim":key,"issue":err})
                report["evidence_checks"]+=len(ev)
                joined=" ".join(e.get("quote","") for e in ev)
                for num in absent_measurements(re.sub(r"\[[^\]]+\]","",body),joined):
                    if state not in {"unreported","uncertain"} and not row.get("derivation"):
                        report["issues"].append({"claim":key,"issue":"number needs source or derivation","value":num})
                for ref in ev:
                    src=sources.get(ref.get("id"))
                    if src:
                        used.add(src["source"]);anchors[ref["id"]]=(src["source"],src["location"])
                        lookup.append([key,title,kind,state,src["source"],src["location"],ref["quote"],row.get("condition","")])
                for word in row.get("keywords",[]): keywords[word.casefold()].append(key)
                if mode=="notes":
                    locs=", ".join(sources[e["id"]]["source"]+"#"+sources[e["id"]]["location"] for e in ev if e["id"] in sources)
                    sentences.append(body+(" 〔"+locs+"〕" if locs else ""))
                else: sentences.append(body)
            if sentences:
                paragraphs.append(("" if plan.get("language") in {"zh","zh-CN"} else " ").join(sentences))
    artifacts={"notes":"notes.md","introduction":"introduction.md","methods":"methods.md"}
    atomic_text(output/artifacts[mode],"\n\n".join(paragraphs)+"\n")
    atomic_text(output/"claim-sources.tsv",tabular(["claim","section","role","status","source","location","quote","condition"],lookup))
    if mode=="notes":
        write(output/"topic-index.json",dict(sorted(keywords.items())))
    if mode=="introduction":
        axes=plan.get("comparisons",[])
        for a in axes:
            for e in check_evidence(a.get("evidence",[]),index["sources"]): report["issues"].append({"comparison":a.get("work"),"issue":e})
            if not a.get("evidence"): report["issues"].append({"comparison":a.get("work"),"issue":"unanchored comparison"})
        write(output/"comparison-matrix.json",axes)
    if mode=="methods":
        params=plan.get("parameters",[])
        for r in params:
            ev=r.get("evidence",[]); state=r.get("status","reported")
            for err in check_evidence(ev,index["sources"]): report["issues"].append({"parameter":r.get("name"),"issue":err})
            value=str(r.get("value","")).strip();unit=str(r.get("unit") or "").strip()
            measured=value+(" "+unit if unit not in {"","1","none","无量纲","dimensionless","—","-"} and unit not in value else "")
            quotes=" ".join(e.get("quote","") for e in ev)
            match=(not absent_measurements(measured,quotes) if quantities(measured) else bool(value) and value in quotes)
            if state=="reported" and (not ev or not match) and not r.get("derivation"):
                report["issues"].append({"parameter":r.get("name"),"issue":"value absent from primary evidence"})
            if state=="conflict" and (len(ev)<2 or not r.get("resolution")):
                report["issues"].append({"parameter":r.get("name"),"issue":"conflict needs alternatives and decision"})
        write(output/"parameters.json",params)
        write(output/"reproduction.json",plan.get("reproduction",{}))
    report["sources_used"]=sorted(used);write(output/"audit.json",report)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=ROLES);p.add_argument("index");p.add_argument("plan");p.add_argument("out",type=Path)
    a=p.parse_args();r=render(a.mode,read(a.index),read(a.plan),a.out);print(f"{r['claims']} claims; {len(r['issues'])} review items")
