"""Use bibliographic wording that can be located in the actual materials."""
import re
import unicodedata

def normalized(text):
    text=unicodedata.normalize("NFKC",text).casefold()
    return re.sub(r"[^\w]+"," ",text).strip()

def reference_labels(requested,rows):
    labels,problems={},[]
    for source,spec in requested.items():
        if isinstance(spec,str):
            parts=[spec]; files=[source]
        elif isinstance(spec,dict):
            parts=spec.get("parts",[]);files=spec.get("sources",[source])
        else:
            parts=[];files=[]
        corpora=[normalized(r["text"]) for r in rows if r["source"] in files]
        if parts and all(isinstance(p,str) and normalized(p) and any((" "+normalized(p)+" ") in (" "+c+" ") for c in corpora) for p in parts):
            labels[source]=". ".join(p.strip().strip(".") for p in parts)
        else:
            problems.append({"source":source,"issues":["bibliographic wording could not be located; source filename retained"]})
    return labels,problems
