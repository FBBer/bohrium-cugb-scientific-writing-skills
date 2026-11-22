"""Verify aligned passages and emit a bilingual or revision manuscript with exact edit spans."""
import argparse
from collections import Counter
from limits import limits, without_limits
import difflib
import re
import unicodedata
from pathlib import Path
from casework import read, write, atomic_text

PATTERNS = {
    "formula":r"(?<!\\)\$\$[\s\S]+?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\n])+?(?<!\\)\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]",
    "citation":r"\[(?:\s*\d+[a-z]?\s*(?:[,，;；–—-]\s*\d+[a-z]?\s*)*)\]|\\(?:cite\w*|ref|eqref)\{[^{}]+\}",
    "quantity":r"(?<![A-Za-z0-9_])(?:[+\-−]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+\-−]?\d+)?)(?:\s*(?:±|×)\s*[+\-−]?\d+(?:\.\d+)?)?(?:\s*(?:%|‰|°C|°F|dBm|dB|[GMkhdcmunpfμµ]?(?:Hz|Pa|mol|rad|kg|g|m|s|L|K|A|W|V|J|T|F|N)(?:/[kmunμµ]?(?:s|m|L|g)(?:[²³23])?)?)(?![A-Za-z]))?",
}
FLAGS={"negative":r"\b(?:not|never|without|neither|nor|no)\b|未|无|不(?:能|会|足|再|存在|表明|显著|显著性)|没有|并非",
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


def linguistic_flags(old,new):
    review=[]
    if limits(old) != limits(new):
        review.append("numeric threshold or inclusive boundary changed")
    old, new = without_limits(old), without_limits(new)
    for key,pattern in FLAGS.items():
        if bool(re.search(pattern,old,re.I))!=bool(re.search(pattern,new,re.I)): review.append(key)
    def directions(text):
        found=sorted((m.start(),key) for key in ("increase","decrease") for m in re.finditer(FLAGS[key],text,re.I))
        return [key for _,key in found]
    left,right=directions(old),directions(new)
    if len(set(left))>1 and Counter(left)==Counter(right) and left!=right:review.append("direction-to-entity assignment")
    return review


def diff(old,new):
    return [{"type":kind,"source_offsets":[i,j],"target_offsets":[k,l],"before":old[i:j],"after":new[k:l]}
            for kind,i,j,k,l in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes() if kind!="equal"]


def audit(source,draft,mode):
    expected=source["segments"]
    gloss=source.get("glossary",{})
    findings=[]; changes=[]; manuscript=[]
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
        for term,target_term in gloss.items():
            expected_term=target_term.get("target") if isinstance(target_term,dict) else target_term
            aliases=target_term.get("accepted",[]) if isinstance(target_term,dict) else []
            if not expected_term: continue
            bound=lambda s: (r"(?<![A-Za-z0-9_])"+re.escape(s)+r"(?![A-Za-z0-9_])") if re.fullmatch(r"[A-Za-z0-9_ -]+",s) else re.escape(s)
            if re.search(bound(term),old,re.I) and not any(re.search(bound(v),target,re.I) for v in [expected_term]+aliases):
                findings.append({"id":key,"issue":"glossary term","source":term,"expected":expected_term})
        review=linguistic_flags(old,target)
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
            manuscript.append(f"### {key} · {where}\n\n{old}\n\n{target}")
        else:
            manuscript.append(target)
    return {"segments_expected":len(expected),"segments_received":len(draft),"findings":findings,"changes":changes}, "\n\n".join(manuscript)+"\n"


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=["translate","edit"]);p.add_argument("source");p.add_argument("draft");p.add_argument("outdir",type=Path);p.add_argument("--strict",action="store_true")
    a=p.parse_args(); report, manuscript=audit(read(a.source),read(a.draft),a.mode)
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
    print(f"{report['segments_received']} segments, {len(report['findings'])} findings")
    if a.strict and report["findings"]: raise SystemExit(1)
