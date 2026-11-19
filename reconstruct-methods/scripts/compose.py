"""Render the author's evidence-mapped writing plan and audit each source quotation."""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal, DecimalException
import io
from pathlib import Path
import re
import unicodedata
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

def condition_substitution(body,condition,evidence):
    if not isinstance(condition,str) or not condition.strip():
        return None
    def normalized(value):
        return " ".join(unicodedata.normalize("NFKC",value).casefold().split())
    sentence=normalized(body);condition=normalized(condition)
    quotes=[normalized(e.get("quote","")) for e in evidence]
    if condition not in sentence or any(condition in quote for quote in quotes):
        return None
    prefix=sentence.partition(condition)[0]
    suffix=sentence.partition(condition)[2].strip(" .,;:，。；：")
    if len(prefix)<8 or not re.search(r"(?:\b(?:in|on|at|under|during|with|without|from)\s+(?:(?:the|a|an)\s+)?|在|处于|位于)$",prefix):
        return None
    for quote in quotes:
        if prefix in quote:
            remaining=quote.partition(prefix)[2].strip(" .,;:，。；：")
            if remaining and (not suffix or suffix in remaining):
                return {"issue":"stated condition substitutes a different source phrase",
                        "stated_condition":condition,"matching_source":quote}
    return None

def derived_measurement(written,evidence,calculation):
    """Verify a two-input derived measurement using quantities in the cited source fragments."""
    if not isinstance(calculation,dict) or not isinstance(calculation.get("inputs"),list):
        return False
    inputs=calculation["inputs"]
    target=quantities(written)
    if len(inputs)!=2 or len(target)!=1:
        return False
    measured=[]
    for term in inputs:
        if not isinstance(term,dict) or "value" not in term or "unit" not in term or not term.get("id"):
            return False
        try:
            value=Decimal(str(term["value"]).replace("−","-"))
        except DecimalException:
            return False
        unit=str(term["unit"]).strip().replace("µ","μ")
        available={pair[:2] for e in evidence if e.get("id")==term["id"] for pair in quantities(e.get("quote",""))}
        if (value,unit) not in available:return False
        measured.append((value,unit))
    (left,u),(right,v)=measured
    if u!=v:return False
    operation=calculation.get("operation")
    try:
        if operation=="sum":number=left+right
        elif operation=="difference":number=left-right
        elif operation=="mean":number=(left+right)/2
        elif operation=="ratio":number=left/right;u=""
        elif operation=="percent_of":number=100*left/right;u="%"
        elif operation=="percent_change":number=100*(left-right)/right;u="%"
        else:return False
        expected,written_unit,_=target[0]
        return u==written_unit and number.quantize(Decimal(1).scaleb(expected.as_tuple().exponent))==expected
    except (DecimalException,ZeroDivisionError):
        return False

NO_DIMENSION=re.compile(r"\b(?:dimensionless|unitless)\b|\b(?:has|have|carries|takes) no (?:physical )?units?\b|无(?:物理)?量纲|无单位",re.I)
NEGATED_DIMENSION=re.compile(r"\b(?:not|never|neither)\s+(?:an?\s+)?(?:dimensionless|unitless)\b|(?:非|不是|并非|并非为|并非是)无(?:物理)?量纲|(?:未|没有)(?:记录|注明|报告|给出|说明)(?:其)?单位|无单位(?:信息|记录|说明|标注)",re.I)
UNSPECIFIED_UNITS={"","none","unknown","unreported","未报告","未知","—","-"}

def explicit_dimensionless(quote):
    return bool(NO_DIMENSION.search(NEGATED_DIMENSION.sub("",quote)))

def supported_cancellation(derivation,quotes):
    if not isinstance(derivation,str):
        return False
    measured=[u for _,u,_ in quantities(quotes) if u]
    for unit in set(measured):
        if measured.count(unit)<2:
            continue
        if (re.search(r"(?<![A-Za-z])"+re.escape(unit)+r"\s*/\s*"+re.escape(unit)+r"(?![A-Za-z])",derivation)
                and re.search(r"(?:[A-Za-z]\w*\s*/\s*[A-Za-z]\w*|ratio of|divided by|除以|之比)",quotes,re.I)):
            return True
    return False

def parameter_unit_issue(row, unit, evidence):
    if unit.casefold() not in {"dimensionless","unitless","无量纲","无单位","1"}:
        return None
    name=str(row.get("name","")).strip().casefold()
    if (name in {"seed","random seed","rng seed","随机种子","iterations","epochs","samples","updates","folds","迭代次数","更新次数","样本数","折数"}
            and re.fullmatch(r"[+-]?\d+",str(row.get("value","")).strip())):
        return None
    quotes=" ".join(e.get("quote","") for e in evidence)
    values={v for v,_,_ in quantities(str(row.get("value","")))}
    contrary=bool(NEGATED_DIMENSION.search(quotes)) or any(v in values and u for v,u,_ in quantities(quotes))
    if not contrary and (explicit_dimensionless(quotes) or supported_cancellation(row.get("unit_derivation"),quotes)):
        return None
    return {"parameter":row.get("name"),"issue":"dimensionless unit needs an explicit source or dimensional derivation","unit":unit}

def tabular(header, rows):
    stream=io.StringIO()
    w=csv.writer(stream,delimiter="\t",lineterminator="\n")
    w.writerow(header);w.writerows(rows)
    return stream.getvalue()

def write_paper_cards(output, notes, comparisons, errors):
    papers={}
    for key,note in notes.items():
        for name,refs in note["sources"].items():
            paper=papers.setdefault(name,{"facts":[],"interpretations":[],"limits":[]})
            field="interpretations" if note["voice"]!="paper" else "limits" if note["role"]=="limitation" else "facts"
            entry={"claim":key,"text":note["text"],"voice":note["voice"],
                   "role":note["role"],"condition":note["condition"],"evidence":refs}
            if note["reason"]:entry["reason"]=note["reason"]
            if len(note["sources"])>1:entry["related_sources"]=note["sources"]
            paper[field].append(entry)
    comparisons_out=[]
    for row in comparisons:
        left,right=row.get("left"),row.get("right")
        if (left not in notes or right not in notes or left==right or not row.get("axis")
                or row.get("comparability") not in {"comparable","conditional","not_comparable"}
                or not row.get("reason")):
            errors.append({"comparison":row.get("axis"),"issue":"comparison needs two supported claims, scale and reason"})
            continue
        comparisons_out.append({**row,"left_sources":notes[left]["sources"],"right_sources":notes[right]["sources"]})
    write(output/"paper-cards.json",{"papers":papers,"comparisons":comparisons_out})


def render(mode, index, plan, output):
    sources={r["id"]:r for r in index["sources"]}
    report={"mode":mode,"issues":[],"sections":[],"claims":0,"evidence_checks":0,"unresolved":[]}
    lookup=[]; paragraphs=[]; anchors={}; keywords=defaultdict(list); used=set(); ids=set()
    card_notes={}
    for section in plan["sections"]:
        title=section["title"]; section_text=[]; report["sections"].append(title)
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
                if state=="supported":
                    changed_condition=condition_substitution(body,row.get("condition"),ev)
                    if changed_condition:report["issues"].append({"claim":key,**changed_condition})
                if (mode=="methods" and kind=="parameter" and state=="supported" and explicit_dimensionless(body)
                        and (NEGATED_DIMENSION.search(joined) or not (explicit_dimensionless(joined) or supported_cancellation(row.get("unit_derivation"),joined)))):
                    report["issues"].append({"claim":key,"issue":"unit assertion needs a source or dimensional derivation"})
                for num in absent_measurements(re.sub(r"\[[^\]]+\]","",body),joined):
                    if not derived_measurement(num,ev,row.get("derivation")):
                        report["issues"].append({"claim":key,"issue":"number needs source or derivation","value":num})
                row_issues=[x for x in report["issues"] if x.get("claim")==key]
                if row_issues:
                    state="needs_review"
                    report["unresolved"].append({"claim":key,"status":state,"candidate":body,"issues":row_issues})
                    body=None
                for ref in ev:
                    src=sources.get(ref.get("id"))
                    if src:
                        used.add(src["source"]);anchors[ref["id"]]=(src["source"],src["location"])
                        lookup.append([key,title,kind,state,src["source"],src["location"],ref["quote"],row.get("condition","")])
                if body is None:continue
                for word in row.get("keywords",[]): keywords[word.casefold()].append(key)
                if mode=="notes":
                    refs=defaultdict(list)
                    for e in ev:
                        if e["id"] in sources:
                            original=sources[e["id"]]
                            refs[original["source"]].append({"location":original["location"],"quote":e["quote"]})
                    voice=("reader" if state=="inference" else "authors" if kind=="interpretation" else "paper")
                    if refs and state not in {"unreported","conflict","uncertain"}:
                        card_notes[key]={"text":body,"role":kind,"voice":voice,"condition":row.get("condition",""),
                                         "reason":row.get("reason",""),"sources":dict(refs)}
                    locs=", ".join(sources[e["id"]]["source"]+"#"+sources[e["id"]]["location"] for e in ev if e["id"] in sources)
                    if state=="inference":
                        body=("读者解读：" if plan.get("language","").startswith("zh") else "Reader’s interpretation — ")+body
                    sentences.append(body+(" 〔"+locs+"〕" if locs else ""))
                else: sentences.append(body)
            if sentences:
                section_text.append(("" if plan.get("language") in {"zh","zh-CN"} else " ").join(sentences))
        if section_text:paragraphs.extend(["## "+title,*section_text])
    artifacts={"notes":"notes.md","introduction":"introduction.md","methods":"methods.md"}
    atomic_text(output/artifacts[mode],"\n\n".join(paragraphs)+"\n")
    atomic_text(output/"claim-sources.tsv",tabular(["claim","section","role","status","source","location","quote","condition"],lookup))
    if mode=="notes":
        write(output/"topic-index.json",dict(sorted(keywords.items())))
        write_paper_cards(output,card_notes,plan.get("comparisons",[]),report["issues"])
    if mode=="introduction":
        axes=plan.get("comparisons",[])
        for a in axes:
            for e in check_evidence(a.get("evidence",[]),index["sources"]): report["issues"].append({"comparison":a.get("work"),"issue":e})
            if not a.get("evidence"): report["issues"].append({"comparison":a.get("work"),"issue":"unanchored comparison"})
        write(output/"comparison-matrix.json",axes)
        contributions=[row for row in lookup if row[2]=="contribution" and row[3]=="supported"]
        atomic_text(output/"contribution-evidence.tsv",tabular(["claim","section","role","status","source","location","quote","condition"],contributions))
    if mode=="methods":
        params=plan.get("parameters",[])
        audited_params=[]
        for original in params:
            r=dict(original)
            ev=r.get("evidence",[]); state=r.get("status","reported")
            for err in check_evidence(ev,index["sources"]): report["issues"].append({"parameter":r.get("name"),"issue":err})
            value=str(r.get("value","")).strip();unit=str(r.get("unit") or "").strip()
            unit_issue=parameter_unit_issue(r,unit,ev)
            if unit_issue:
                report["issues"].append(unit_issue)
                r["unit"]=None
                r["unit_status"]="unreported"
            measured=value+(" "+unit if unit.casefold() not in UNSPECIFIED_UNITS|{"1","dimensionless","unitless","无量纲","无单位"} and unit not in value else "")
            quotes=" ".join(e.get("quote","") for e in ev)
            match=(not absent_measurements(measured,quotes) if quantities(measured) else bool(value) and value in quotes)
            if unit_issue and len(quantities(value))==1:
                match=any(number==quantities(value)[0][0] for number,_,_ in quantities(quotes))
            if state in {"reported","conflict"} and r.get("value") is not None and (not ev or not match) and not derived_measurement(measured,ev,r.get("derivation")):
                report["issues"].append({"parameter":r.get("name"),"candidate":value,"issue":"value absent from primary evidence"})
                r["value"]=None
                r["value_status"]="unsupported"
            if state=="conflict" and (len(ev)<2 or not r.get("resolution")):
                report["issues"].append({"parameter":r.get("name"),"issue":"conflict needs alternatives and decision"})
            audited_params.append(r)
        write(output/"parameters.json",audited_params)
        write(output/"reproduction.json",plan.get("reproduction",{}))
    report["sources_used"]=sorted(used);report["status"]="partial" if report["issues"] else "complete"
    write(output/"audit.json",report)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=ROLES);p.add_argument("index");p.add_argument("plan");p.add_argument("out",type=Path);p.add_argument("--strict",action="store_true")
    a=p.parse_args();r=render(a.mode,read(a.index),read(a.plan),a.out);print(f"{r['claims']} claims; {len(r['issues'])} review items")
    if a.strict and r["issues"]:raise SystemExit(1)
