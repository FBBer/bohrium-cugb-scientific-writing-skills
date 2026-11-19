"""Serialize evidence-checked atomic claims as standard four-graph nanopublications."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from casework import read,write,atomic_text,check_evidence

PREFIX='''@prefix np: <http://www.nanopub.org/nschema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix c: <urn:scholar:field:> .
'''
def literal(x): return json.dumps(str(x),ensure_ascii=False)
def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()[:24]
def uri(name): return "<urn:scholar:"+name+">"


def export(index,record,out):
    sources={s["id"]:s for s in index["sources"]};blocks=[];accepted=[];issues=[];seen=set()
    meta=record.get("papers",{})
    for item in record["claims"]:
        key=item.get("id");evidence=item.get("evidence",[])
        errors=check_evidence(evidence,index["sources"])
        for field in ("subject","predicate","object","statement","scope","polarity","evidence_type"):
            if not isinstance(item.get(field),str) or not item[field].strip(): errors.append("missing "+field)
        if item.get("evidence_type") not in {"direct","inference","reported-by-others"}: errors.append("unknown evidence type")
        if item.get("polarity") not in {"positive","negative","uncertain"}: errors.append("unknown polarity")
        if not evidence: errors.append("needs a minimal original quotation")
        if item.get("evidence_type")=="inference" and not item.get("reason"): errors.append("missing inferential bridge")
        if errors:
            issues.append({"id":key,"reasons":errors});continue
        payload={k:item[k] for k in ("subject","predicate","object","scope","polarity","evidence_type","statement")}
        bindings=sorted((sources[e["id"]]["source"],sources[e["id"]]["location"],e["quote"]) for e in evidence)
        source_editions={source:meta.get(source,{}) for source,_,_ in bindings}
        sid=digest([payload,bindings,source_editions,record.get("publication",{})])
        if sid in seen: continue
        seen.add(sid)
        base="np:"+sid
        n,h,a,p,i=[uri(base+suffix) for suffix in ("",":head",":assertion",":provenance",":pubinfo")]
        claim=uri(base+":claim")
        graphs=[f"{h} {{ {n} a np:Nanopublication ; np:hasAssertion {a} ; np:hasProvenance {p} ; np:hasPublicationInfo {i} . }}"]
        fields=" ; ".join("c:"+k+" "+literal(v) for k,v in payload.items())
        graphs.append(f"{a} {{ {claim} a c:QualifiedClaim ; {fields} . }}")
        triples=[]
        for j,(source,location,fragment) in enumerate(bindings,1):
            ev=uri(base+f":e{j}");document=uri("doc:"+quote(source,safe="")+":"+digest(source_editions[source]))
            triples.extend([f"{a} prov:wasDerivedFrom {ev} .", f"{ev} prov:wasQuotedFrom {document} ; c:location {literal(location)} ; rdf:value {literal(fragment)} .",
                            f"{document} dct:identifier {literal(source)} ."])
            paper=meta.get(source,{})
            for attr in ("title","identifier","date","hasVersion","creator"):
                values=paper.get(attr,[]);values=values if isinstance(values,list) else [values]
                for value in values: triples.append(f"{document} dct:{attr} {literal(value)} .")
        graphs.append(p+" {\n  "+"\n  ".join(triples)+"\n}")
        info=[f"{n} dct:conformsTo <https://nanopub.net/guidelines/working_draft/> ."]
        for attr in ("creator","created","hasVersion"):
            if record.get("publication",{}).get(attr): info.append(f"{n} dct:{attr} {literal(record['publication'][attr])} .")
        graphs.append(i+" { "+" ".join(info)+" }");blocks.extend(graphs)
        accepted.append({**item,"nanopub_id":"urn:scholar:"+base})
    atomic_text(out/"nanopubs.trig",PREFIX+"\n\n"+"\n\n".join(blocks)+"\n")
    write(out/"assertions.json",{"claims":accepted,"source_metadata":meta,"unresolved":issues})
    return accepted,issues
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("index");p.add_argument("claims");p.add_argument("out",type=Path)
    a=p.parse_args();rows,issues=export(read(a.index),read(a.claims),a.out);print(f"{len(rows)} nanopublications, {len(issues)} unresolved")
