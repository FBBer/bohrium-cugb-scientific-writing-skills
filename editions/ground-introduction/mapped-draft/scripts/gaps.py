"""Trace a bounded literature gap to the authors' stated limitations or matched disagreement."""
import re
from comparisons import norm, compare_evidence
from manuscript import reported_directions

UNIVERSAL=re.compile(r"\b(?:no (?:previous |prior )?(?:stud(?:y|ies)|research|work) (?:has|have|exists?)|never (?:been )?(?:tested|examined|studied)|first (?:ever|in the world))\b|全球首[个次]|从未有(?:人|研究)|尚无任何研究",re.I)
RESTRICTED=re.compile(r"\b(?:only|limited to|restricted to|excluded|not (?:tested|measured|studied|assessed|investigated|reported|evaluated)|did not (?:test|measure|assess|study|report)|unmeasured|outside (?:the |our )?scope)\b|仅限|仅在|尚未|未(?:在|测|检|评|纳入|覆盖|考察|报告)|不在.{0,8}范围",re.I)

def derive_gap(claim,refs,own):
    g=claim.get("gap") or {}
    scope=g.get("scope","").strip()
    if not scope or norm(scope) not in norm(claim["text"]):
        raise ValueError("state the scope of the gap in the manuscript sentence")
    if UNIVERSAL.search(claim["text"]):raise ValueError("the available studies do not support a universal gap")
    filenames={r["file"] for r in refs}
    if not filenames or filenames & set(own):raise ValueError("use prior-study evidence for a literature gap")
    if set(g.get("papers",[]))!=filenames:raise ValueError("the stated scope must identify its cited papers")
    kind=g.get("kind","limitation")
    if kind=="limitation":
        for f in filenames:
            if not any(RESTRICTED.search(r["quote"]) for r in refs if r["file"]==f):
                raise ValueError("no explicit scope restriction in "+f)
    elif kind=="disagreement":
        matrix=compare_evidence(g["comparison"],refs)
        if matrix["differing_dimensions"]:raise ValueError("study conditions differ")
        outcomes=[]
        for f in filenames:
            obs=reported_directions(" ".join(r["quote"] for r in refs if r["file"]==f))
            if len(obs)!=1 or next(iter(obs))[1]:raise ValueError("an explicit direction is absent for "+f)
            outcomes.append(next(iter(obs))[0])
        if len(set(outcomes))!=2:raise ValueError("the evidence does not show opposing directions")
    else:raise ValueError("unknown gap basis")
    return {"kind":kind,"scope":scope,"papers":sorted(filenames),"evidence":refs}
