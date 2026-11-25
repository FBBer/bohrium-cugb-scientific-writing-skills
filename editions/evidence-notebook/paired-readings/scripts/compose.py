"""Render the author's evidence-mapped writing plan and audit each source quotation."""
import argparse
from collections import defaultdict
import csv
from decimal import Decimal, DecimalException, localcontext, ROUND_HALF_UP
import io
from pathlib import Path
import re
import unicodedata
from casework import read, write, atomic_text, check_evidence

ROLES={
    "notes":{"question","data","method","finding","limitation","definition","context","interpretation"},
    "introduction":{"background","comparison","gap","objective","contribution","scope"},
    "methods":{"procedure","data","split","parameter","evaluation","baseline","environment","repetition","limitation"}}
UNIT_POWER = r"(?:[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+|\^(?:\{[+−-]?\d+\}|[+−-]?\d+))?"
UNIT_ATOM = r"(?:°[CF]|dBm|dB|[kMGTcmunμµ]?(?:Hz|Pa|V|W|A|K|J|g|m|s|L|F|N|T|mol))"+UNIT_POWER
UNIT = r"(?:%|‰|"+UNIT_ATOM+r"(?:(?:[ \t]*[/·⋅][ \t]*|[ \t]+)"+UNIT_ATOM+r")*(?![A-Za-z]))"
NUMBER = re.compile(r"(?<![A-Za-z0-9_.])([+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?)(?:[ \t]*("+UNIT+r"))?")
def quantities(text):
    return [(Decimal(m[1].replace("−","-")),(m[2] or "").replace("µ","μ"),m[0].strip()) for m in NUMBER.finditer(text)]

def absent_measurements(sentence,source):
    known={(value,unit) for value,unit,_ in quantities(source)}
    return [raw for value,unit,raw in quantities(sentence) if (value,unit) not in known]


def spreadsheet_units(sources):
    """Associate numeric cells with a unit header within the same continuous column."""
    columns=defaultdict(list); formats={}
    for item in sources:
        if item["source"].lower().endswith((".csv",".tsv")):
            cell = re.fullmatch(r"R([1-9]\d*):C([1-9]\d*)",item["location"])
            if cell:
                columns[item["source"],"delimited",cell[2]].append((int(cell[1]),item))
            continue
        if item["source"].lower().endswith(".docx"):
            cell = re.fullmatch(r"word/document\.xml:tbl(\d+):R(\d+):C(\d+)", item["location"])
            if cell:
                columns[item["source"],cell[1],cell[3]].append((int(cell[2]),item))
            continue
        if not item["source"].lower().endswith(".xlsx"):
            continue
        if item["location"].endswith(":format"):
            formats[item["source"],item["location"][:-7]]=item
            continue
        cell=re.fullmatch(r"('(?:[^']|'')+')!([A-Z]+)([1-9]\d*)(?::cached)?",item["location"])
        if cell:
            columns[item["source"],cell[1],cell[2]].append((int(cell[3]),item))
    result={}
    for cells in columns.values():
        header=None; previous=0
        for row,item in sorted(cells,key=lambda pair:pair[0]):
            if row!=previous+1:
                header=None
            previous=row
            text=item["text"].strip()
            if re.fullmatch(r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+−-]?\d+)?",text):
                style=formats.get((item["source"],item["location"].removesuffix(":cached")))
                if style and re.fullmatch(r"0(?:\.0+)?%",style["text"]):
                    precision=style["text"].count("0")-1
                    stored=Decimal(text.replace("−","-"))
                    if abs(stored.adjusted())>308 or precision>30:
                        continue
                    with localcontext() as context:
                        context.prec=max(34,len(stored.as_tuple().digits)+3,stored.adjusted()+precision+5)
                        amount=stored*100
                        displayed=amount.quantize(Decimal(1).scaleb(-precision),rounding=ROUND_HALF_UP)
                    with_unit=[str(amount)+"%",str(displayed)+"%"]
                    result[item["id"]]=(item["text"],style["id"],style["text"],with_unit)
                elif header:
                    header_id,header_text,unit=header
                    result[item["id"]]=(item["text"],header_id,header_text,[text+" "+unit])
                continue
            header=None
            label=re.search(r"(?:\(([^()]+)\)|\[([^\[\]]+)\]|_([^_\s]+))\s*$",text)
            if label:
                unit=next(v.strip() for v in label.groups() if v)
                recognized=NUMBER.fullmatch("1 "+unit)
                if recognized and recognized[2]==unit:
                    header=(item["id"],item["text"],unit)
    return result


def evidence_quantities_text(evidence, units, sources, header_evidence=None):
    parts=[]
    for ref in evidence:
        source=sources.get(ref.get("id"),{})
        if source.get("source","").lower().endswith(".xlsx") and source.get("location","").endswith((":format",":formula")):
            continue
        parts.append(ref.get("quote",""))
    literal={(ref.get("id"),ref.get("quote")) for ref in (evidence if header_evidence is None else header_evidence)}
    for ref in evidence:
        pair=units.get(ref.get("id"))
        if pair:
            value,header_id,header_text,measurements=pair
            if ref.get("quote")==value and (header_id,header_text) in literal:
                parts.extend(measurements)
    return "\n".join(parts)

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

SI_UNIT = re.compile(r"([TGMkcmuμn]?)(Hz|Pa|V|W|A|K|J|g|m|s|L|F|N|T|mol)")
SI_EXPONENT = {"T":12,"G":9,"M":6,"k":3,"":0,"c":-2,"m":-3,"u":-6,"μ":-6,"n":-9}


def derived_measurement(written,evidence,calculation,cell_units=None):
    """Verify an explicit unit conversion or two-input calculation against cited quantities."""
    if not isinstance(calculation,dict) or not isinstance(calculation.get("inputs"),list):
        return False
    inputs=calculation["inputs"]
    target=quantities(written)
    operation=calculation.get("operation")
    if len(inputs)!=(1 if operation=="convert_unit" else 2) or len(target)!=1:
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
        literal = {(e.get("id"), e.get("quote")) for e in evidence}
        available={pair[:2] for e in evidence if e.get("id")==term["id"] for pair in quantities(e.get("quote",""))}
        cell = (cell_units or {}).get(term["id"])
        if cell:
            raw, header_id, header, readings = cell
            if (term["id"],raw) in literal and (header_id,header) in literal:
                available.update(pair[:2] for reading in readings for pair in quantities(reading))
        if (value,unit) not in available:return False
        measured.append((value,unit))
    if operation=="convert_unit":
        before, source_unit=measured[0]
        after, target_unit, _=target[0]
        source=SI_UNIT.fullmatch(source_unit)
        dest=SI_UNIT.fullmatch(target_unit)
        if not source or not dest or source[2]!=dest[2]:
            return False
        try:
            # The change of SI prefix is exact; equality needs no tolerance or guessed factor.
            with localcontext() as context:
                context.prec=max(34,len(before.as_tuple().digits)+1)
                return before.scaleb(SI_EXPONENT[source[1]]-SI_EXPONENT[dest[1]])==after
        except DecimalException:
            return False
    (left,u),(right,v)=measured
    if u!=v:return False
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

SOURCE_CLAUSES = re.compile(r"[;；。！？!?\r\n]|(?<!\d)\.(?=\s+[A-Z]|$)|(?<=\d)\.(?=\s+[A-Z]|$)|\b(?:whereas|while|but)\b|但是|然而|而(?=另一|第|样|試|试|组|对照)", re.I)


def bound_clause(quote, subject, condition):
    if not all(isinstance(x, str) and x.strip() for x in (quote, subject, condition)):
        return False
    def has(phrase, clause):
        phrase = phrase.strip()
        start = r"(?<![A-Za-z0-9])" if re.match(r"[A-Za-z0-9]", phrase) else ""
        end = r"(?![A-Za-z0-9])" if re.search(r"[A-Za-z0-9]$", phrase) else ""
        return bool(re.search(start + re.escape(phrase) + end, clause, re.I))
    return any(has(subject, clause) and has(condition, clause) for clause in SOURCE_CLAUSES.split(quote))


SYMBOL = r"[A-Za-zα-ωΑ-Ω](?:[A-Za-z0-9₀-₉]*)(?:_(?:\{[A-Za-z0-9]+\}|[A-Za-z0-9]+))?"
SIMPLE_RATIO = re.compile(r"(?<![A-Za-z0-9_/])("+SYMBOL+r")\s*=\s*\(?\s*("+SYMBOL+r")\s*\)?\s*/\s*\(?\s*("+SYMBOL+r")(?![A-Za-z0-9₀-₉_])")


def reversed_definition(text, original):
    def symbol(key):
        return unicodedata.normalize("NFKC",key).replace("_","").replace("{","").replace("}","")
    definitions = {(symbol(a),symbol(b),symbol(c)) for a,b,c in SIMPLE_RATIO.findall(original)}
    return any(b!=c and (a,c,b) in definitions and (a,b,c) not in definitions
               for a,b,c in (tuple(map(symbol,m)) for m in SIMPLE_RATIO.findall(text)))


def verify_target_bindings(bindings, body):
    groups = defaultdict(list)
    for binding in bindings:
        amount = str(binding.get("condition_in_source") or "")
        quantity = quantities(amount)
        if len(quantity)!=1 or quantity[0][2]!=amount.strip() or not quantity[0][1]:
            continue
        groups[(binding.get("id"),binding.get("quote",""))].append((binding,quantity[0][:2]))
    for (_, passage), pairs in groups.items():
        if len(pairs)<2 or len({q for _,q in pairs})!=len(pairs):
            continue
        source_seq = [q[:2] for q in quantities(passage)]
        target_seq = [q[:2] for q in quantities(body)]
        if not all(source_seq.count(q)==1 and target_seq.count(q)==1 for _,q in pairs):
            continue
        anchored = True
        for binding,q in pairs:
            name = binding.get("subject_in_text") or binding.get("subject_in_source")
            spans = [clause for clause in re.split(r"[，；。;]|,(?!\d)|\b(?:whereas|while|but)\b",body,flags=re.I)
                     if name and re.search(re.escape(name),clause,re.I)]
            if len(spans)==1:
                if q not in [z[:2] for z in quantities(spans[0])]:
                    return "target assigns the cited measurement to a different named subject"
            else:
                anchored = False
        values={q for _,q in pairs}
        if not anchored and [q for q in source_seq if q in values]!=[q for q in target_seq if q in values]:
            return "verify reordered measurements against their subjects; give subject_in_text for a translated or reordered clause"
    return None


def binding_errors(bindings, evidence, source_rows):
    problems = []
    for binding in bindings:
        ref = {"id":binding.get("id"), "quote":binding.get("quote")}
        if ref not in evidence or check_evidence([ref], source_rows):
            problems.append({"issue":"unverified attribution anchor"})
            continue
        pair = [binding.get("subject_in_source",""),binding.get("condition_in_source","")]
        if not bound_clause(ref["quote"], *pair):
            problems.append({"issue":"subject and condition do not share the asserted source clause","terms":pair,"anchor":ref["id"]})
    return problems


def table_context(index):
    """Relate numeric table cells to the category values occurring in their actual rows."""
    fields = {r["id"]:r["text"] for r in index["sources"]}
    by_value,domains = defaultdict(list),defaultdict(set)
    for row in index.get("records",[]):
        if not row["source"].lower().endswith((".csv",".tsv")):
            continue
        categories,readings = {},[]
        for f in row["fields"]:
            value = fields[f["id"]].strip()
            if re.fullmatch(r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+−-]?\d+)?",value):
                readings.append((f,Decimal(value.replace("−","-"))))
            elif len(value)<=60 and re.search(r"[^\W\d_]",value) and "\n" not in value:
                column = (row["source"],f["column"])
                domains[column].add(value)
                categories[column] = value
        for f,number in readings:
            measure = (row["source"],f["column"],number)
            by_value[f["id"]].append((measure,categories))
    return by_value,domains


def named_group(label,text):
    left = r"(?<![A-Za-z0-9])" if re.match(r"[A-Za-z0-9]",label) else ""
    right = r"(?![A-Za-z0-9])" if re.search(r"[A-Za-z0-9]$",label) else ""
    if len(label)==1 and label.isascii() and label.isalpha():
        # A single letter in running prose may be an article, a variable or a unit.
        if text.strip()==label:
            return True
        return bool(re.search(r"(?:\b(?:group|sample|run|series|site)\s+|组|样品|条件)"+re.escape(label)+right,text))
    return bool(re.search(left+re.escape(label)+right,text,re.I))


def wrong_table_group(evidence, body, context, source_rows, scope=None):
    by_value,domains = context
    linked = defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
    for e in evidence:
        if e.get("quote")!=source_rows.get(e.get("id"),{}).get("text"):
            continue
        for (file,reading_column,number),labels in by_value.get(e.get("id"),[]):
            for col,label in labels.items():
                if len(domains[col])>=2:
                    linked[file,reading_column][col][number].add(label)

    def named(column, words):
        hits = [label for label in domains[column] if named_group(label,words)]
        specific = [v for v in hits if not any(v.casefold() in other.casefold() for other in hits if v!=other)]
        return sorted(specific,key=lambda label:words.casefold().find(label.casefold()))

    def mismatch(written, allowed, number, column):
        locations = []
        for ref in evidence:
            item=source_rows.get(ref.get("id"),{})
            if ref.get("quote")==item.get("text") and any(
                    measure[2]==number and labels.get(column) in allowed for measure,labels in by_value.get(ref.get("id"),[])):
                point={"source":item["source"],"location":item["location"],"quote":ref["quote"]}
                if point not in locations:
                    locations.append(point)
        return {"issue":"the written group and the cited measurement belong to different table rows","source_locations":locations,
                "written_groups":sorted(written-allowed),"source_groups":sorted(allowed),"measurement":str(number)}

    for sentence in re.split(r"[;；。!?！？]|(?<!\d)\.(?=\s|$)",body):
        all_numbers=[v for v,_,_ in quantities(sentence)]
        for columns in linked.values():
            for col,allowed in columns.items():
                if scope is not None:
                    for number in all_numbers:
                        given=set(named(col,str(scope)))
                        if number in allowed and given-allowed[number]:
                            return mismatch(given,allowed[number],number,col)
                    continue
                if re.search(r"\brespectively\b|in that order|分别|依次",sentence,re.I):
                    names = named(col,sentence)
                    readings = [v for v in all_numbers if v in allowed]
                    if len(names)==len(readings) and len(names)>=2:
                        for label,number in zip(names,readings):
                            if label not in allowed[number]:
                                return mismatch({label},allowed[number],number,col)
                        continue
                inherited = set()
                for clause in re.split(r"[，,]|\b(?:whereas|while|but)\b",sentence,flags=re.I):
                    given = set(named(col,clause))
                    numbers = [v for v,_,_ in quantities(clause) if v in allowed]
                    if not numbers:
                        if given:
                            inherited = given
                        continue
                    subjects = given or inherited
                    for number in numbers:
                        if subjects-allowed[number]:
                            return mismatch(subjects,allowed[number],number,col)
                    if given:
                        inherited = given
    return None


def observation_errors(index, observations, evidence):
    from source_records import lookup
    verified = {(r["id"],r["quote"]) for r in evidence}
    problems = []
    for o in observations:
        criteria = o.get("where")
        if not isinstance(criteria,dict) or not criteria or not all(isinstance(v,str) for v in criteria.values()):
            problems.append("supply the exact group and conditions for the selected observation")
            continue
        try:
            found = lookup(index,o.get("source"),criteria.items(),[o.get("field")],2)
        except ValueError as error:
            problems.append(str(error))
            continue
        if found["total"] != 1 or len(found["matches"][0]["values"])!=1:
            problems.append("source and group must identify one observation and one value column")
            continue
        row = found["matches"][0]
        cell = row["values"][0]
        if cell["id"] != o.get("value_id") or any((r["id"],r["quote"]) not in verified for r in row["matched_fields"]+[cell]):
            problems.append("the cited value and group must belong to the same observed row")
    return problems


def tabular(header, rows):
    stream=io.StringIO()
    w=csv.writer(stream,delimiter="\t",lineterminator="\n")
    w.writerow(header);w.writerows(rows)
    return stream.getvalue()

def write_paper_cards(output, notes, comparisons, errors, boundaries):
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
    unassigned = []
    for entry in boundaries:
        if not entry["sources"]:
            unassigned.append(entry)
        for name, refs in entry["sources"].items():
            paper = papers.setdefault(name, {"facts":[],"interpretations":[],"limits":[]})
            paper.setdefault("boundaries",[]).append({**entry,"evidence":refs})
    write(output/"paper-cards.json",{"papers":papers,"comparisons":comparisons_out,"unassigned_boundaries":unassigned})


def render(mode, index, plan, output, word=False, preview=False):
    sources={r["id"]:r for r in index["sources"]}
    sheet_units=spreadsheet_units(index["sources"])
    table_groups=table_context(index)
    report={"mode":mode,"issues":[],"sections":[],"claims":0,"evidence_checks":0,"unresolved":[]}
    lookup=[]; paragraphs=[]; anchors={}; keywords=defaultdict(list); used=set(); ids=set()
    card_notes={}; note_boundaries=[]; word_sections=[]; audited_params=[]
    for section in plan["sections"]:
        title=section["title"]; section_text=[]; report["sections"].append(title); word_groups=[]
        for group in section.get("paragraphs",[]):
            sentences=[]; word_group=[]
            for row in group:
                key=row["id"]; kind=row["role"]; body=row["text"]
                if key in ids: report["issues"].append({"claim":key,"issue":"duplicate id"})
                ids.add(key);report["claims"]+=1
                if kind not in ROLES[mode]: report["issues"].append({"claim":key,"issue":"unknown role "+kind})
                ev=row.get("evidence",[]); state=row.get("status","supported")
                # A valid quotation may still be attributed to the wrong study or condition.
                for problem in binding_errors(row.get("bindings",[]),ev,index["sources"]):
                    report["issues"].append({"claim":key,**problem})
                for problem in observation_errors(index,row.get("observations",[]),ev):
                    report["issues"].append({"claim":key,"issue":problem})
                if state in {"unreported","conflict","inference","uncertain"}:
                    report["unresolved"].append({"claim":key,"status":state,"reason":row.get("reason",""),"evidence":ev})
                    if not row.get("reason"): report["issues"].append({"claim":key,"issue":"explain uncertainty or inference"})
                if not ev and state not in {"unreported","uncertain"}: report["issues"].append({"claim":key,"issue":"missing evidence"})
                for err in check_evidence(ev,index["sources"]): report["issues"].append({"claim":key,"issue":err})
                report["evidence_checks"]+=len(ev)
                joined=evidence_quantities_text(ev,sheet_units,sources)
                if state=="supported":
                    group_issue=wrong_table_group(ev,body,table_groups,sources)
                    if group_issue:
                        report["issues"].append({"claim":key,**group_issue})
                    if reversed_definition(body,joined):
                        report["issues"].append({"claim":key,"issue":"the source formula reverses the numerator and denominator of this definition"})
                    assignment = verify_target_bindings(row.get("bindings",[]),body)
                    if assignment:
                        report["issues"].append({"claim":key,"issue":assignment})
                    changed_condition=condition_substitution(body,row.get("condition"),ev)
                    if changed_condition:report["issues"].append({"claim":key,**changed_condition})
                if (mode=="methods" and kind=="parameter" and state=="supported" and explicit_dimensionless(body)
                        and (NEGATED_DIMENSION.search(joined) or not (explicit_dimensionless(joined) or supported_cancellation(row.get("unit_derivation"),joined)))):
                    report["issues"].append({"claim":key,"issue":"unit assertion needs a source or dimensional derivation"})
                for num in absent_measurements(re.sub(r"\[[^\]]+\]","",body),joined):
                    if not derived_measurement(num,ev,row.get("derivation"),sheet_units):
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
                    if state in {"unreported","conflict","uncertain"}:
                        note_boundaries.append({"claim":key,"text":body,"status":state,"reason":row.get("reason",""),"sources":dict(refs)})
                    if refs and state not in {"unreported","conflict","uncertain"}:
                        card_notes[key]={"text":body,"role":kind,"voice":voice,"condition":row.get("condition",""),
                                         "reason":row.get("reason",""),"sources":dict(refs)}
                    locs=", ".join(sources[e["id"]]["source"]+"#"+sources[e["id"]]["location"] for e in ev if e["id"] in sources)
                    if state=="inference":
                        body=("读者解读：" if plan.get("language","").startswith("zh") else "Reader’s interpretation — ")+body
                    sentences.append(body+(" 〔"+locs+"〕" if locs else ""))
                else: sentences.append(body)
                if word or preview:
                    word_group.append((body,ev))
            if sentences:
                section_text.append(("" if plan.get("language") in {"zh","zh-CN"} else " ").join(sentences))
            if word_group: word_groups.append(word_group)
        if word_groups: word_sections.append((title,word_groups))
        if section_text:paragraphs.extend(["## "+title,*section_text])
    artifacts={"notes":"notes.md","introduction":"introduction.md","methods":"methods.md"}
    atomic_text(output/artifacts[mode],"\n\n".join(paragraphs)+"\n")
    atomic_text(output/"claim-sources.tsv",tabular(["claim","section","role","status","source","location","quote","condition"],lookup))
    if mode=="notes":
        write(output/"topic-index.json",dict(sorted(keywords.items())))
        write_paper_cards(output,card_notes,plan.get("comparisons",[]),report["issues"],note_boundaries)
    if mode=="introduction":
        axes=[]
        for comparison in plan.get("comparisons",[]):
            evidence=comparison.get("evidence",[])
            problems=check_evidence(evidence,index["sources"]) if evidence else ["unanchored comparison"]
            problems.extend(item["issue"] for item in binding_errors(comparison.get("bindings",[]), evidence, index["sources"]))
            if evidence and not problems:
                quoted=evidence_quantities_text(evidence,sheet_units,sources)
                result_text=str(comparison.get("observed_result") or "")
                for number in absent_measurements(result_text,quoted):
                    if not derived_measurement(number,evidence,comparison.get("derivation"),sheet_units):
                        problems.append("comparison result lacks source or derivation: "+number)
            if problems:
                report["issues"].extend({"comparison":comparison.get("work"),"issue":reason} for reason in problems)
                report["unresolved"].append({"comparison":comparison,"reasons":problems})
            else:
                axes.append(comparison)
        write(output/"comparison-matrix.json",axes)
        contributions=[row for row in lookup if row[2]=="contribution" and row[3]=="supported"]
        atomic_text(output/"contribution-evidence.tsv",tabular(["claim","section","role","status","source","location","quote","condition"],contributions))
    if mode=="methods":
        params=plan.get("parameters",[])
        audited_params=[]
        for original in params:
            r=dict(original)
            ev=[]; state=r.get("status","reported")
            for item in r.get("evidence",[]):
                errors=check_evidence([item],index["sources"])
                if errors:
                    report["issues"].append({"parameter":r.get("name"),"issue":errors[0]})
                    report["unresolved"].append({"parameter":r.get("name"),"candidate_evidence":item})
                else:
                    ev.append(item)
            r["evidence"]=ev
            value=str(r.get("value","")).strip();unit=str(r.get("unit") or "").strip()
            unit_issue=parameter_unit_issue(r,unit,ev)
            if unit_issue:
                report["issues"].append(unit_issue)
                r["unit"]=None
                r["unit_status"]="unreported"
            measured=value+(" "+unit if unit.casefold() not in UNSPECIFIED_UNITS|{"1","dimensionless","unitless","无量纲","无单位"} and unit not in value else "")
            selected = r.get("selected_evidence")
            value_refs = ev
            if selected is not None:
                value_refs = [ref for ref in ev if ref == selected]
                if not value_refs:
                    report["issues"].append({"parameter":r.get("name"),"issue":"selected run evidence must be one of the verified quotations"})
            scope_issue=wrong_table_group(value_refs,measured,table_groups,sources,scope=r.get("scope")) if r.get("scope") else None
            if scope_issue and state in {"reported","conflict"}:
                report["issues"].append({"parameter":r.get("name"),"candidate":value,**scope_issue})
                r["value"]=None
                r["value_status"]="unsupported_group"
            quotes=evidence_quantities_text(value_refs,sheet_units,sources,header_evidence=ev)
            match=(not absent_measurements(measured,quotes) if quantities(measured) else bool(value) and value in quotes)
            if unit_issue and len(quantities(value))==1:
                match=any(number==quantities(value)[0][0] for number,_,_ in quantities(quotes))
            if state in {"reported","conflict"} and r.get("value") is not None and (not value_refs or not match) and not derived_measurement(measured,value_refs,r.get("derivation"),sheet_units):
                report["issues"].append({"parameter":r.get("name"),"candidate":value,"issue":"value absent from primary evidence"})
                r["value"]=None
                r["value_status"]="unsupported"
                if not ev:
                    r["unit"]=None
                    r["unit_status"]="unreported"
            if state=="conflict" and (len(ev)<2 or not r.get("resolution")):
                report["issues"].append({"parameter":r.get("name"),"issue":"conflict needs alternatives and decision"})
            audited_params.append(r)
        write(output/"parameters.json",audited_params)
        write(output/"reproduction.json",plan.get("reproduction",{}))
    report["sources_used"]=sorted(used);report["status"]="partial" if report["issues"] else "complete"
    write(output/"audit.json",report)
    if word or preview:
        from manuscript_word import export
        export(mode,plan,word_sections,audited_params,sources,(output/artifacts[mode]).with_suffix(".docx"),preview)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=ROLES);p.add_argument("index");p.add_argument("plan");p.add_argument("out",type=Path);p.add_argument("--strict",action="store_true")
    p.add_argument("--word",action="store_true",help="write an editable manuscript with linked source passages")
    p.add_argument("--preview",action="store_true",help="render the editable manuscript as PDF with LibreOffice")
    a=p.parse_args();r=render(a.mode,read(a.index),read(a.plan),a.out,a.word,a.preview);print(f"{r['claims']} claims; {len(r['issues'])} review items")
    if a.strict and r["issues"]:raise SystemExit(1)
