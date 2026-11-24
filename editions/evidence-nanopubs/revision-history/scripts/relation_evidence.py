"""Resolve unambiguous active/passive clauses for common directed scholarly relations."""
import re

VERBS = ("use uses used", "measure measures measured", "evaluate evaluates evaluated",
         "calibrate calibrates calibrated", "validate validates validated", "predict predicts predicted",
         "detect detects detected", "support supports supported", "reduce reduces reduced",
         "increase increases increased", "improve improves improved", "compare compares compared")
QUAL = r"(?:(?:do|does|did|is|are|was|were|have|has|had|be|been|being|not|never|may|might|could|can|possibly|directly|also|only|significantly)\s+)*"
ARTICLE = r"(?:(?:the|an?)\s+)?"


def direction_readings(quote, predicate, subjects, targets):
    base = (predicate or "").strip().casefold().replace("_"," ")
    forms = next((v.split() for v in VERBS if base in v.split()),None)
    if not forms:
        return set()
    def names(labels):
        return r"(?<![\w-])(?:"+"|".join(re.escape(n) for n in sorted(set(labels),key=len,reverse=True) if n)+r")(?![\w-])"
    verb = "(?:"+"|".join(forms)+")"
    readings = set()
    for sign,left,right in ((1,subjects,targets),(-1,targets,subjects)):
        active = names(left)+r"\s+(?P<qual>"+QUAL+")"+verb+r"\s+"+ARTICLE+names(right)
        passive = names(right)+r"\s+(?P<qual>"+QUAL+")"+forms[-1]+r"\s+by\s+"+ARTICLE+names(left)
        for pattern in (active,passive):
            for match in re.finditer(pattern,quote,re.I):
                qualifier = match["qual"].casefold()
                lead = re.split(r"[.!?;。！？；,，]|\b(?:but|whereas)\b",quote[:match.start()],flags=re.I)[-1]
                tentative = (re.search(r"\b(?:may|might|could|can|possibly)\b",qualifier) or
                             re.search(r"\b(?:if|whether|hypothes\w*|assum\w*)\b|\bno evidence\b",lead,re.I))
                qualifier = re.sub(r"\bnot only\b","",qualifier)
                negatives = len(re.findall(r"\b(?:not|never)\b",qualifier))
                polarity = "uncertain" if tentative or negatives>1 else "negative" if negatives else "positive"
                readings.add((sign,polarity))
    return readings


def incompatible_relation(quote, predicate, subjects, targets, polarity, *, quoted_tentative=False):
    seen = direction_readings(quote,predicate,subjects,targets)
    if not seen:
        return False
    if not any(direction==1 for direction,_ in seen):
        return True
    if quoted_tentative and (1, "uncertain") in seen:
        wording = re.sub(r"\b(?:may|might|could|can|possibly)\b\s*", "", quote, flags=re.I)
        if polarity == "uncertain" or (1, polarity) in direction_readings(wording, predicate, subjects, targets):
            return False
    return polarity in {"positive","negative"} and (1,polarity) not in seen
