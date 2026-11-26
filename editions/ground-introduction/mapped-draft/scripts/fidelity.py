"""Keep experimental claims attached to the paper, status, result and figure that support them."""
import re
from compose import absent_measurements
from manuscript import reported_directions, CAUSAL, ASSOCIATION, NONCAUSAL
from comparisons import norm

PLAN=re.compile(r"\b(?:will|planned|proposed to|aim(?:s|ed)? to|intend(?:s|ed)? to)\b|计划|拟(?:开展|测试|进行|验证)|将(?:测量|检验|测试)",re.I)
OBSERVED=re.compile(r"\b(?:observed|confirmed|demonstrated|measured|achieved|outperformed|validated|reduced)\b|证实|实测|测得|验证了|优于|降低了",re.I)
FIG=re.compile(r"(fig(?:ure)?\.?|tab(?:le)?\.?|图|表)\s*([A-Za-z]?\d+(?:[.-]\d+)*[a-z]?)",re.I)
def figures(text):
    return {("figure" if m[1].lower().startswith("fig") or m[1]=="图" else "table",m[2].casefold()) for m in FIG.finditer(text)}

def fidelity(role,claim,refs,own):
    text=claim.get("text","")
    sources={a["file"] for a in refs}
    if role=="contribution" and (not sources or sources-set(own)):
        return ["the contribution needs the current study's own records"]
    excerpts=" ".join(a["quote"] for a in refs)
    problems=[]
    facts=absent_measurements(text,excerpts)
    if facts:problems.append("quantity or unit outside its sources: "+", ".join(facts))
    if figures(text)-figures(excerpts):problems.append("unmatched figure or table identifier")
    if role=="contribution" and OBSERVED.search(text) and not PLAN.search(text) and refs and all(PLAN.search(a["quote"]) for a in refs):
        problems.append("a planned experiment cannot substantiate a measured outcome")
    if CAUSAL.search(text) and not NONCAUSAL.search(text) and (ASSOCIATION.search(excerpts) or NONCAUSAL.search(excerpts)) and (not CAUSAL.search(excerpts) or NONCAUSAL.search(excerpts)):
        problems.append("the reported association does not establish causality")
    directions=reported_directions(excerpts); asserted=reported_directions(text)
    if len(directions)==1 and asserted and not asserted.issubset(directions):
        problems.append("change direction or negation differs from the source")
    if len(sources)>1 and re.search(r"\d",text) and any(absent_measurements(text," ".join(a["quote"] for a in refs if a["file"]==f)) for f in sources):
        problems.append("attach each numerical result to a separate source-backed clause")
    return problems
