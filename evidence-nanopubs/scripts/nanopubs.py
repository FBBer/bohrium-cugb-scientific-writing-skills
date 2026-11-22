"""Serialize evidence-checked atomic claims as standard four-graph nanopublications."""
import argparse
from relation_evidence import incompatible_relation
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from casework import read,write,atomic_text,check_evidence
from passages import locate

PREFIX='''@prefix np: <http://www.nanopub.org/nschema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix oa: <http://www.w3.org/ns/oa#> .
@prefix c: <urn:scholar:field:> .
'''
def literal(x): return json.dumps(str(x),ensure_ascii=False)
def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()[:24]
def uri(name): return "<urn:scholar:"+name+">"


def evidence_selectors(evidence, document, selection):
    """Both selectors address the same Unicode text block in the same document edition."""
    identity = [document, selection["location"], selection["block_sha256"]]
    block = uri("block:" + digest(identity))
    return [
        f"{block} dct:isPartOf {document} ; dct:identifier {literal(selection['location'])} ; "
        f"c:blockSha256 {literal(selection['block_sha256'])} .",
        f"{evidence} a oa:SpecificResource ; oa:hasSource {block} ; "
        f"oa:hasSelector [ a oa:TextPositionSelector ; oa:start {selection['start']} ; oa:end {selection['end']} ], "
        f"[ a oa:TextQuoteSelector ; oa:exact {literal(selection['exact'])} ; "
        f"oa:prefix {literal(selection['prefix'])} ; oa:suffix {literal(selection['suffix'])} ] .",
    ]

MODAL_TERMS=re.compile(r"\b(?:may|might|could|possibly|probably|(?:un)?likely(?:\s+to)?|suggest(?:s|ed)?|consistent with|cannot rule out|cannot exclude)\b|可能|或可|倾向于|提示|推测|无法排除|不能排除|与.{1,12}相符",re.I)
COMPARATIVES=re.compile(r"\b(higher|greater|more|larger|lower|less|smaller)\b|(高于|大于|多于|低于|小于|少于)",re.I)
INCREASING={"higher","greater","more","larger","高于","大于","多于"}

def oriented_comparison(text,subject,other):
    """Read the direction only when the same two objects bracket an explicit comparator."""
    plain=text.casefold();a=plain.find(subject.casefold());b=plain.find(other.casefold())
    if min(a,b)<0 or a==b:return None
    start,end=(a+len(subject),b) if a<b else (b+len(other),a)
    clause=plain[start:end]
    if re.search(r"[;；!?。！？]|\b(?:not|never|without)\b|[未不]",clause):return None
    signs={1 if m[0] in INCREASING else -1 for m in COMPARATIVES.finditer(clause)}
    if len(signs)==1:return signs.pop()*(1 if a<b else -1)
    return None

def source_cues(text):
    for match in MODAL_TERMS.finditer(text):
        if match[0]=="May":
            left=text[max(0,match.start()-18):match.start()]
            right=text[match.end():match.end()+12]
            if (re.match(r"\s+\d{1,4}\b",right)
                    or re.search(r"\b(?:[0-3]?\d(?:st|nd|rd|th)?|in|during|since|until|last|next|early|late|mid)\s*[- ]?$",left,re.I)):
                continue
        yield match[0]

def modality(item,evidence):
    quotes=[str(e.get("quote","")) for e in evidence]
    cues=list(dict.fromkeys(cue for fragment in quotes for cue in source_cues(fragment)))
    supplied=item.get("source_modality")
    if supplied:
        if not isinstance(supplied,str) or not any(supplied.casefold() in fragment.casefold() for fragment in quotes):
            return None,"modality wording must occur in the cited passage"
        if supplied not in cues:cues.append(supplied)
    strength=item.get("claim_strength")
    if strength and strength not in {"reported","tentative","inferred"}:
        return None,"unknown claim strength"
    if item.get("evidence_type")=="inference":
        strength="inferred"
    elif strength=="reported" and (cues or item.get("polarity")=="uncertain") and not item.get("modality_context"):
        strength="tentative"
    if not strength:
        strength="tentative" if cues or item.get("polarity")=="uncertain" else "reported"
    summary={"claim_strength":strength,"source_cues":cues}
    if item.get("claim_strength") and item["claim_strength"]!=strength:
        summary["strength_adjustment"]={"submitted":item["claim_strength"],"applied":strength}
    return summary,None


def relation_terms(item, source_editions):
    terms = {}
    for role in ("subject","predicate","object"):
        explicit = item.get(role+"_iri")
        if explicit is not None:
            if not isinstance(explicit,str) or not re.fullmatch(r'(?:https?://[^/\s]+/[^\s]*|urn:[a-zA-Z0-9][a-zA-Z0-9-]*:[^\s]+)',explicit) or re.search(r'[<>"{}|^\x60\\\x00-\x20]',explicit):
                raise ValueError("invalid "+role+"_iri")
            terms[role]=explicit
        else:
            # Identical labels without a shared supplied identifier do not merge across independent sources.
            identity = [item[role].strip(), item["scope"], source_editions]
            namespace = "predicate:" if role=="predicate" else "entity:"
            terms[role] = "urn:scholar:" + namespace + digest(identity)
    return terms


def export(index,record,out):
    from readings import readings
    sources={s["id"]:s for s in index["sources"]};blocks=[];accepted=[];issues=[];seen=set()
    meta=record.get("papers",{})
    for item in record["claims"]:
        key=item.get("id");evidence=item.get("evidence",[])
        errors=check_evidence(evidence,index["sources"])
        selected = []
        if not errors:
            for ref in evidence:
                try:
                    selected.append(locate(sources[ref["id"]], ref))
                except ValueError as exc:
                    errors.append(f"{ref['id']}: {exc}")
        for field in ("subject","predicate","object","statement","scope","polarity","evidence_type"):
            if not isinstance(item.get(field),str) or not item[field].strip(): errors.append("missing "+field)
        if item.get("evidence_type") not in {"direct","inference","reported-by-others"}: errors.append("unknown evidence type")
        if item.get("polarity") not in {"positive","negative","uncertain"}: errors.append("unknown polarity")
        if not evidence: errors.append("needs a minimal original quotation")
        if item.get("evidence_type")=="inference" and not item.get("reason"): errors.append("missing inferential bridge")
        qualifiers,err=modality(item,evidence)
        if err:errors.append(err)
        if not errors and item["evidence_type"]=="direct":
            asserted = readings(item["statement"])
            cited = {quantity for ref in evidence for quantity in readings(ref["quote"])}
            missing = [printed for quantity, printed in asserted.items() if quantity not in cited]
            if missing:
                errors.append("measurement not in the cited passages: " + ", ".join(missing))
            statement = " ".join(item["statement"].casefold().split())
            incompatible = []
            for e in evidence:
                # A verbatim tentative finding may be recorded with its modality attached.
                # Do not turn a paraphrase or an unqualified positive/negative into that finding.
                tentative = (qualifiers["claim_strength"] == "tentative"
                             and bool(qualifiers["source_cues"])
                             and statement == " ".join(e["quote"].casefold().split()))
                if incompatible_relation(e["quote"], item["predicate"], [item["subject"]], [item["object"]],
                                         item["polarity"], quoted_tentative=tentative):
                    incompatible.append(e)
            if incompatible:
                errors.append("a cited clause reverses or qualifies this direct relation")
            direction=oriented_comparison(item["statement"],item["subject"],item["object"])
            sources_signs={oriented_comparison(e["quote"],item["subject"],item["object"]) for e in evidence}-{None}
            if direction and sources_signs=={-direction}:
                errors.append("comparative direction contradicts the quoted order of the same two entities")
        if errors:
            issues.append({"id":key,"reasons":errors});continue
        payload={k:item[k] for k in ("subject","predicate","object","scope","polarity","evidence_type","statement")}
        payload["claim_strength"]=qualifiers["claim_strength"]
        if item.get("modality_context"):payload["modality_context"]=item["modality_context"]
        if item.get("reason"):payload["reason"]=item["reason"]
        bindings=sorted((sources[e["id"]]["source"],sources[e["id"]]["location"],e["quote"]) for e in evidence)
        source_editions={source:meta.get(source,{}) for source,_,_ in bindings}
        try:
            terms = relation_terms(item, source_editions)
        except ValueError as exc:
            issues.append({"id":key,"reasons":[str(exc)]})
            continue
        selected.sort(key=lambda s:(s["source"],s["location"],s["exact"],s["start"]))
        sid=digest([payload,terms,qualifiers["source_cues"],selected,source_editions,record.get("publication",{})])
        if sid in seen: continue
        seen.add(sid)
        base="np:"+sid
        n,h,a,p,i=[uri(base+suffix) for suffix in ("",":head",":assertion",":provenance",":pubinfo")]
        claim=uri(base+":claim")
        graphs=[f"{h} {{ {n} a np:Nanopublication ; np:hasAssertion {a} ; np:hasProvenance {p} ; np:hasPublicationInfo {i} . }}"]
        fields=" ; ".join("c:"+k+" "+literal(v) for k,v in payload.items())
        for cue in qualifiers["source_cues"]:
            fields+=" ; c:source_modality "+literal(cue)
        subject, predicate, obj = ("<"+terms[role]+">" for role in ("subject","predicate","object"))
        reification = f"{claim} a c:QualifiedClaim, rdf:Statement ; rdf:subject {subject} ; rdf:predicate {predicate} ; rdf:object {obj} ; {fields} ."
        # A reified description does not assert its triple. Assert the scoped relation only for direct positive observations.
        triples = [reification]
        if item["polarity"]=="positive" and item["evidence_type"]=="direct" and qualifiers["claim_strength"]=="reported":
            triples.append(f"{subject} {predicate} {obj} .")
        graphs.append(a + " { " + " ".join(triples) + " }")
        triples=[]
        for j,selection in enumerate(selected,1):
            source,location,fragment=(selection[k] for k in ("source","location","exact"))
            ev=uri(base+f":e{j}");document=uri("doc:"+quote(source,safe="")+":"+digest(source_editions[source]))
            triples.extend([f"{a} prov:wasDerivedFrom {ev} .", f"{ev} prov:wasQuotedFrom {document} ; c:location {literal(location)} ; rdf:value {literal(fragment)} .",
                            f"{document} dct:identifier {literal(source)} ."])
            triples.append(f"{ev} c:start {selection['start']} ; c:end {selection['end']} ; "
                           f"c:prefix {literal(selection['prefix'])} ; c:suffix {literal(selection['suffix'])} ; "
                           f"c:blockSha256 {literal(selection['block_sha256'])} .")
            triples.extend(evidence_selectors(ev, document, selection))
            paper=meta.get(source,{})
            for attr in ("title","identifier","date","hasVersion","creator"):
                values=paper.get(attr,[]);values=values if isinstance(values,list) else [values]
                for value in values: triples.append(f"{document} dct:{attr} {literal(value)} .")
        graphs.append(p+" {\n  "+"\n  ".join(triples)+"\n}")
        info=[f"{n} dct:conformsTo <https://nanopub.net/guidelines/working_draft/> ."]
        for attr in ("creator","created","hasVersion","license"):
            if record.get("publication",{}).get(attr): info.append(f"{n} dct:{attr} {literal(record['publication'][attr])} .")
        graphs.append(i+" { "+" ".join(info)+" }");blocks.extend(graphs)
        accepted.append({**item,**qualifiers,"passages":selected,"relation_iris":terms,"nanopub_id":"urn:scholar:"+base})
    atomic_text(out/"nanopubs.trig",PREFIX+"\n\n"+"\n\n".join(blocks)+"\n")
    write(out/"assertions.json",{"claims":accepted,"source_metadata":meta,"unresolved":issues})
    return accepted,issues
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("index");p.add_argument("claims");p.add_argument("out",type=Path)
    a=p.parse_args();rows,issues=export(read(a.index),read(a.claims),a.out);print(f"{len(rows)} nanopublications, {len(issues)} unresolved")
