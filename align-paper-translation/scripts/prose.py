"""Verify aligned passages and emit a bilingual or revision manuscript with exact edit spans."""
import argparse
from collections import Counter
import difflib
import re
import unicodedata
from pathlib import Path
from casework import read, write, atomic_text

UNIT_POWER = r"(?:[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+|\^(?:\{[+−-]?\d+\}|[+−-]?\d+))?"
UNIT_ATOM = r"(?:°[CF]|dBm|dB|[GMkhdcmunpfμµ]?(?:Hz|Pa|mol|rad|kg|g|m|s|L|K|A|W|V|J|T|F|N))" + UNIT_POWER
MEASURE_UNIT = r"(?:%|‰|" + UNIT_ATOM + r"(?:(?:[ \t]*[/·⋅][ \t]*|[ \t]+)" + UNIT_ATOM + r")*(?![A-Za-z]))"

PATTERNS = {
    "formula":r"(?<!\\)\$\$[\s\S]+?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\n])+?(?<!\\)\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]",
    "citation":r"\[(?:\s*\d+[a-z]?\s*(?:[,，;；–—-]\s*\d+[a-z]?\s*)*)\]|\\(?:cite\w*|ref|eqref)\{[^{}]+\}",
    "quantity": r"(?<![A-Za-z0-9_])(?:[+\-−]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+\-−]?\d+)?)(?:\s*(?:±|×)\s*[+\-−]?\d+(?:\.\d+)?)?(?:\s*" + MEASURE_UNIT + r")?",
}
FLAGS={"negative":r"\b(?:not|cannot|never|without|neither|nor|no)\b|\b(?:ca|wo|do|does|did|is|are|was|were|have|has|had|could|would|should)n['’]t\b|未|无|不(?!同|少|仅|论|管|变量|等式|锈钢|确定性)|没有|并非",
       "hedge":r"\b(?:might|may|could|suggest\w*|approximately|potential\w*|consistent with)\b|可能|提示|大约|约为|相符",
       "causal":r"\b(?:caus\w*|led to|resulted in)\b|导致|引起|造成",
       "condition":r"\b(?:only|unless|provided that|if|except|under)\b|仅|只有|如果|若|除非|条件下",
       "increase":r"\b(?:higher|greater|larger|increas\w*|exceed\w*|above|positive(?:ly)?)\b|高于|大于|增加|增大|升高|正相关",
       "decrease":r"\b(?:lower|smaller|less|decreas\w*|reduc\w*|below|negative(?:ly)?)\b|低于|小于|降低|降低了|减少|下降|负相关",
       "cessation_or_persistence":r"\b(?:stop(?:s|ped|ping)?|ceas\w*|continu\w*|persist\w*|remain(?:s|ed)?)\b|停止|持续|继续|不再|仍然",
       "negation_scope":r"\b(?:cannot|can not|could not|not)\s+(?:rule out|exclude|fail to|stop|cease|prevent)\b|(?:不能|无法|未能|未|没有|并未)(?:排除|否认|停止|阻止)|并非没有"}
def protected(text):
    work=unicodedata.normalize("NFC",text)
    out={}
    for k,pattern in PATTERNS.items():
        matches=list(re.finditer(pattern,work))
        values=[re.sub(r"\s+","",m.group()).replace("−","-").replace("µ","μ") for m in matches]
        out[k]=Counter(values)
        chars=list(work)
        for m in matches: chars[m.start():m.end()]=" "*len(m.group())
        work="".join(chars)
    return out


CLAUSE_BREAKS=r"\b(?:and|or|but|whereas|while|yet|however|although)\b|[;；]|(?<!\d)[,，](?!\d)|但是|然而|并且|而且|同时|或者|但|而(?=[^且])|并(?!(?:非|未|无|不|没有))"

def split_clauses(text):
    return [part for part in re.split(CLAUSE_BREAKS,text,flags=re.I) if part.strip(" ,，。.")]

SYMBOL = r"[A-Za-zα-ωΑ-Ω](?:[A-Za-z0-9₀-₉]*)(?:_(?:\{[A-Za-z0-9]+\}|[A-Za-z0-9]+))?"
SIMPLE_RATIO = re.compile(r"(?<![A-Za-z0-9_/])("+SYMBOL+r")\s*=\s*\(?\s*("+SYMBOL+r")\s*\)?\s*/\s*\(?\s*("+SYMBOL+r")(?![A-Za-z0-9₀-₉_])")


def reversed_definition(text, original):
    def symbol(key):
        return unicodedata.normalize("NFKC",key).replace("_","").replace("{","").replace("}","")
    definitions = {(symbol(a),symbol(b),symbol(c)) for a,b,c in SIMPLE_RATIO.findall(original)}
    return any(b!=c and (a,c,b) in definitions and (a,b,c) not in definitions
               for a,b,c in (tuple(map(symbol,m)) for m in SIMPLE_RATIO.findall(text)))


def linguistic_flags(old,new,gloss=None):
    review=["reversed numerator and denominator"] if reversed_definition(new,old) else []
    for key,pattern in FLAGS.items():
        if bool(re.search(pattern,old,re.I))!=bool(re.search(pattern,new,re.I)): review.append(key)
    def directions(text):
        found=sorted((m.start(),key) for key in ("increase","decrease") for m in re.finditer(FLAGS[key],text,re.I))
        return [key for _,key in found]
    left,right=directions(old),directions(new)
    if len(set(left))>1 and Counter(left)==Counter(right) and left!=right:review.append("direction-to-entity assignment")
    source_clauses,target_clauses=split_clauses(old),split_clauses(new)
    original=[bool(re.search(FLAGS["negative"],p,re.I)) for p in source_clauses]
    revised=[bool(re.search(FLAGS["negative"],p,re.I)) for p in target_clauses]
    pairs=set()
    if gloss and min(len(original),len(revised))>1:
        for term,spec in gloss.items():
            spec={"target":spec} if isinstance(spec,str) else spec
            aliases=spec.get("accepted",[])
            accepted=[spec.get("target"),*([aliases] if isinstance(aliases,str) else aliases)]
            source_pos=[i for i,p in enumerate(source_clauses) if term_spans(p,term)]
            target_pos=[i for i,p in enumerate(target_clauses) if any(term_spans(p,a) for a in accepted)]
            if len(source_pos)==len(target_pos)==1:pairs.add((source_pos[0],target_pos[0]))
    semantic_swap=any(original[i]!=revised[j] for i,j in pairs)
    if len(original)>1 and len(original)==len(revised) and sum(original)==sum(revised) and original!=revised:
        one_to_one=len({i for i,j in pairs})==len({j for i,j in pairs})==len(pairs)
        known_reorder=(one_to_one and len(pairs)>=len(original)-1 and any(i!=j for i,j in pairs) and not semantic_swap)
        if not known_reorder:review.append("negation assigned to a different clause")
    elif semantic_swap:
        review.append("negation linked to a different glossary entity")
    def negated_heads(text):
        return {m[1].casefold() for m in re.finditer(r"\b(?:not|never|cannot|didn['’]t|doesn['’]t|don['’]t)\s+(?:(?:ever|significantly|directly|consistently)\s+)?([a-z]{3,})\b",text,re.I)}
    if re.search(r"[A-Za-z]",old) and re.search(r"[A-Za-z]",new):
        lost=negated_heads(old)-negated_heads(new)
        gained=negated_heads(new)-negated_heads(old)
        def shared_predicate(words,text):
            return any(re.search(r"\b"+re.escape(w[:-1] if w.endswith("e") else w)+r"(?:e|es|s|ed|d|ing)?\b",text,re.I) for w in words)
        if lost and gained and shared_predicate(lost,new) and shared_predicate(gained,old):
            review.append("different predicate is negated")
    return review


def diff(old,new):
    return [{"type":kind,"source_offsets":[i,j],"target_offsets":[k,l],"before":old[i:j],"after":new[k:l]}
            for kind,i,j,k,l in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes() if kind!="equal"]

MARKER=re.compile(r"⟪[A-Z][A-Z0-9_:. -]{0,48}⟫|⟦[A-Z][A-Z0-9_:. -]{0,48}⟧|__(?:MATH|FORMULA|CITE|TERM|PLACEHOLDER|TEMP)(?:[_:-][A-Za-z0-9.-]+)*__",re.ASCII)

def term_spans(text,term):
    if not isinstance(term,str) or not term.strip():
        return []
    pattern=re.escape(term)
    if re.fullmatch(r"[A-Za-z0-9_ -]+",term):
        pattern=r"(?<![A-Za-z0-9_])"+pattern+r"(?![A-Za-z0-9_])"
    return [m.span() for m in re.finditer(pattern,text,re.I)]

def glossary_issues(source,target,term,spec):
    if not term_spans(source,term):
        return []
    if isinstance(spec,str):
        spec={"target":spec}
    preferred=spec.get("target")
    aliases=spec.get("accepted",[])
    forbidden=spec.get("forbidden",[])
    if isinstance(aliases,str): aliases=[aliases]
    if isinstance(forbidden,str): forbidden=[forbidden]
    findings=[]
    accepted_spans=[span for t in [preferred,*aliases] for span in term_spans(target,t)]
    if preferred and not accepted_spans:
        findings.append({"issue":"glossary term","source":term,"expected":preferred})
    for wrong in forbidden:
        matches=term_spans(target,wrong)
        if any(not any(a<=start and stop<=b and (a,b)!=(start,stop) for a,b in accepted_spans) for start,stop in matches):
            findings.append({"issue":"forbidden glossary variant","source":term,"variant":wrong,"expected":preferred})
    return findings


def audit(source,draft,mode):
    expected=source["segments"]
    gloss=source.get("glossary",{})
    findings=[]; changes=[]; manuscript=[]; alignment=[]
    ids=[r["id"] for r in expected]; seen=[r.get("id") for r in draft]
    if len(set(ids))!=len(ids): findings.append({"issue":"duplicate source segment id"})
    if ids!=seen: findings.append({"issue":"order or coverage differs","expected":ids,"actual":seen})
    by_id={r["id"]:r for r in expected}
    for row in draft:
        key=row.get("id"); target=row.get("target",""); item=by_id.get(key)
        if not item: continue
        old=item["text"]; where=item.get("location",key)
        if not isinstance(target,str) or not target.strip():
            findings.append({"id":key,"issue":"empty target"}); continue
        before,after=protected(old),protected(target)
        for kind,left in before.items():
            right=after[kind]
            if left!=right:
                findings.append({"id":key,"issue":"protected "+kind,"missing":list((left-right).elements()),"added":list((right-left).elements())})
        ordered=lambda t:[re.sub(r"\s+","",m.group()).replace("−","-").replace("µ","μ") for m in re.finditer(PATTERNS["quantity"],t)]
        seq_a,seq_b=ordered(old),ordered(target)
        if seq_a!=seq_b and Counter(seq_a)==Counter(seq_b) and len(set(seq_a))>1:
            findings.append({"id":key,"issue":"review quantity-to-entity assignment","source_order":seq_a,"target_order":seq_b})
        added_markers=Counter(MARKER.findall(target))-Counter(MARKER.findall(old))
        if added_markers:
            findings.append({"id":key,"issue":"unresolved placeholder","markers":dict(added_markers)})
        for term,spec in gloss.items():
            findings.extend({"id":key,**result} for result in glossary_issues(old,target,term,spec))
        review=linguistic_flags(old,target,gloss)
        if review: findings.append({"id":key,"issue":"semantic review","categories":review})
        for label,pattern in {"figure":r"(?:\bfig(?:ure)?\.?|图)\s*([0-9]+[a-z]?)",
                              "table":r"(?:\btable|表)\s*([0-9]+[a-z]?)",
                              "equation":r"(?:\beq(?:uation)?\.?|公式|式)\s*\(?([0-9]+[a-z]?)\)?"}.items():
            left=Counter(re.findall(pattern,old,re.I))
            right=Counter(re.findall(pattern,target,re.I))
            if left!=right: findings.append({"id":key,"issue":label+" reference", "source":dict(left),"target":dict(right)})
        if mode=="edit" and old!=target:
            changes.append({"id":key,"location":where,"original":old,"revised":target,"type":row.get("type"),"reason":row.get("reason"),"edits":diff(old,target)})
            if not row.get("reason") or not row.get("type"):
                findings.append({"id":key,"issue":"missing change classification or explanation"})
        if mode=="translate":
            alignment.append({"id":key,"location":where,"original":old,"target":target})
            manuscript.append(f"### {key} · {where}\n\n{old}\n\n{target}")
        else:
            manuscript.append(target)
    report={"segments_expected":len(expected),"segments_received":len(draft),"findings":findings,"changes":changes}
    if mode=="translate":report["alignment"]=alignment
    return report, "\n\n".join(manuscript)+"\n"


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=["translate","edit"]);p.add_argument("source");p.add_argument("draft");p.add_argument("outdir",type=Path);p.add_argument("--strict",action="store_true")
    p.add_argument("--word",action="store_true",help="also export an editable parallel text or clean and tracked Word manuscripts")
    p.add_argument("--original-docx",type=Path,help="revise anchored plain paragraphs in the original Word template")
    p.add_argument("--preview",action="store_true",help="also render the Word deliverables as PDF using LibreOffice")
    a=p.parse_args(); source,draft=read(a.source),read(a.draft);report, manuscript=audit(source,draft,a.mode)
    name="bilingual.md" if a.mode=="translate" else "revised.md"
    report["status"]="needs_review" if report["findings"] else "checked"
    write(a.outdir/"audit.json",report)
    if a.strict and report["findings"]:
        canonical=a.outdir/name
        if canonical.is_file():
            import hashlib
            canonical.replace(a.outdir/("previous-"+hashlib.sha256(canonical.read_bytes()).hexdigest()[:12]+"-"+name))
        name="candidate-"+name
    atomic_text(a.outdir/name,manuscript)
    if a.word or a.original_docx or a.preview:
        import subprocess
        from word_export import export_word,preview_pdf
        try:
            candidate = a.strict and report["findings"]
            if candidate:
                import hashlib
                names = ["bilingual.docx"] if a.mode=="translate" else ["tracked.docx","revised.docx"]
                for filename in names:
                    canonical = a.outdir/filename
                    if canonical.is_file() and (not a.original_docx or canonical.resolve()!=a.original_docx.resolve()):
                        canonical.replace(a.outdir/("previous-"+hashlib.sha256(canonical.read_bytes()).hexdigest()[:12]+"-"+filename))
            export_word(a.mode,source,draft,a.outdir,"candidate-" if candidate else "",a.original_docx)
            if a.preview:
                prefix="candidate-" if candidate else ""
                names=["bilingual"] if a.mode=="translate" else ["revised","tracked"]
                cjk=a.mode=="translate" or any(re.search(r"[\u3400-\u9fff]",r.get("target","")) for r in draft)
                for name in names:
                    preview_pdf(a.outdir/(prefix+name+".docx"),cjk)
        except (ValueError, ImportError, OSError, subprocess.SubprocessError) as exc:
            p.exit(1, str(exc)+"\n")
    print(f"{report['segments_received']} segments, {len(report['findings'])} findings")
    if a.strict and report["findings"]: raise SystemExit(1)
