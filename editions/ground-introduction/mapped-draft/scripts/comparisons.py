"""Check each study's comparison conditions against its own source passages."""
import re
import unicodedata

def norm(value):
    return " ".join(unicodedata.normalize("NFKC",str(value)).split()).casefold()

def compare_evidence(spec, refs):
    files=list(dict.fromkeys(r["file"] for r in refs))
    if len(files)<2:raise ValueError("comparison requires two distinct papers")
    terms=spec["by_source"]
    if set(terms)!=set(files):raise ValueError("reference and comparison source sets differ")
    fields=set().union(*(row.keys() for row in terms.values()))
    if not {"metric","condition"}.issubset(fields):raise ValueError("specify metric and condition for each paper")
    normalized={};rows=[]
    for f in files:
        details=terms[f]
        if set(details)!=fields:raise ValueError("a comparison dimension is missing for "+f)
        source=" ".join(norm(r["quote"]) for r in refs if r["file"]==f)
        for k,v in details.items():
            if not isinstance(v,str) or not norm(v) or not re.search(r"(?<![A-Za-z0-9])"+re.escape(norm(v))+r"(?![A-Za-z0-9])",source):
                raise ValueError("ungrounded "+k+" in "+f)
        normalized[f]={k:norm(v) for k,v in details.items()}
        rows.append({"file":f,"values":details,"evidence":[r for r in refs if r["file"]==f]})
    unequal=sorted(k for k in fields if len({normalized[f][k] for f in files})>1)
    mode=spec.get("kind","contrast")
    if mode not in ("contrast","rank"):raise ValueError("unknown comparison kind")
    if mode=="rank" and unequal:
        raise ValueError("performance ranking mixes "+", ".join(unequal))
    return {"kind":mode,"papers":rows,"differing_dimensions":unequal}
