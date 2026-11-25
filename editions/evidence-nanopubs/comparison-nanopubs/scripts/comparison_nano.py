"""Serialize comparisons as nanopublications with the exact evidence for each observation."""
from decimal import Decimal
from hashlib import sha256
import json
import re
from edition_io import main, require, anchor
from sourcebook import dump, h, html_page, html_table, link

UNITS={"mm":("m","0.001"),"cm":("m","0.01"),"m":("m","1"),
       "ms":("s","0.001"),"s":("s","1"),"min":("s","60"),"%":("%","1")}
def digest(obj):
    return sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def lit(v):
    return json.dumps(str(v),ensure_ascii=False)
def dec(v):
    return format(v.normalize(),"f")
def measure(sourcebook,row,unit):
    a=anchor(sourcebook,row["evidence"])
    label=row["label"].strip()
    require(label and label.casefold() in a["quote"].casefold(),"specify the arm label as it appears in the excerpt")
    dimension,scale=UNITS.get(unit,(unit,"1"))
    seen_dim,factor=UNITS.get(row["unit"],(row["unit"],"1"))
    require(seen_dim==dimension,"cannot compare unlike dimensions")
    number=Decimal(str(row["value"]))
    require(number.is_finite(),"measurement must be finite")
    found=[]
    for match in re.finditer(r"(?<![\d.])([+−-]?\d+(?:\.\d+)?)\s*"+re.escape(row["unit"])+r"(?![A-Za-z])",a["quote"]):
        if Decimal(match[1].replace("−","-"))==number:
            context=a["quote"][:match.start()]
            require(not re.search(r"(?:[<>≤≥~≈]|at (?:least|most)|about|approximately|至少|至多|约)\s*$",context,re.I),"a bound or approximation cannot be treated as an exact observation")
            found.append(match)
    require(len(found)==1,"the excerpt must contain one occurrence of the stated measurement")
    return number*Decimal(factor)/Decimal(scale),a
def render(sources,plan,out):
    """Publish each supported pair with a separate assertion, evidence graph and publication graph."""
    ttl=['@prefix np: <http://www.nanopub.org/nschema#> .',
         '@prefix prov: <http://www.w3.org/ns/prov#> .','@prefix dct: <http://purl.org/dc/terms/> .',
         '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .','@prefix obs: <urn:bohr:observation:> .']
    data=[];refs=[];seen=set()
    for spec in plan["comparisons"]:
        unit=spec["unit"]; scope=spec["scope"]
        require(scope.strip() and spec["version"].strip(),"scope and source version are required")
        scope_ref=anchor(sources,spec["scope_evidence"])
        require(scope.casefold() in scope_ref["quote"].casefold(),"the scope must occur in its passage")
        va,ea=measure(sources,spec["reference"],unit)
        vb,eb=measure(sources,spec["comparison"],unit)
        lhs,rhs=spec["reference"]["label"],spec["comparison"]["label"]
        require(lhs!=rhs and ea["ref"]!=eb["ref"],"two distinct arms and observations required")
        for e in (ea,eb):
            require(scope.casefold() in e["quote"].casefold() or (scope_ref["source"]==e["source"] and spec.get("single_scope_document") is True),"scope is not linked to both arms")
        diff=vb-va;direction="higher" if diff>0 else "lower" if diff<0 else "equal"
        if spec.get("expected_direction"):
            require(spec["expected_direction"]==direction,"stated direction conflicts with observations")
        evidence=[ea,eb,scope_ref]
        source_hashes={a["source"]:sha256((sources.root/a["source"]).read_bytes()).hexdigest() for a in evidence}
        facts=dict(reference=lhs,comparison=rhs,reference_value=dec(va),comparison_value=dec(vb),difference=dec(diff),
                   unit=unit,scope=scope,direction=direction,version=spec["version"],evidence=evidence,source_hashes=source_hashes)
        uri="urn:sha256:"+digest(facts)
        require(uri not in seen,"duplicate assertion")
        seen.add(uri)
        def u(s=""):
            return "<"+uri+s+">"
        ttl.extend([u("#head")+" { "+u()+" a np:Nanopublication ; np:hasAssertion "+u("#assertion")+" ; np:hasProvenance "+u("#provenance")+" ; np:hasPublicationInfo "+u("#pubinfo")+" . }",
          u("#assertion")+" { "+u("#contrast")+" a obs:ObservedContrast ; obs:reference "+lit(lhs)+" ; obs:comparison "+lit(rhs)+
          " ; obs:referenceValue "+lit(dec(va))+"^^xsd:decimal ; obs:comparisonValue "+lit(dec(vb))+"^^xsd:decimal ; obs:delta "+lit(dec(diff))+
          "^^xsd:decimal ; obs:unit "+lit(unit)+" ; obs:scope "+lit(scope)+" ; obs:direction "+lit(direction)+" . }"])
        prov=[]
        for key,a in zip(("Reference","Comparison","Scope"),evidence):
            node=u("#"+key)
            prov.append(u("#assertion")+" prov:wasDerivedFrom "+node+" .")
            prov.append(node+" a prov:Entity ; obs:role "+lit(key)+" ; dct:source "+lit(a["source"])+" ; dct:isVersionOf "+lit(spec["version"])+
                        " ; obs:fileSHA256 "+lit(source_hashes[a["source"]])+" ; obs:location "+lit(a["loc"])+" ; prov:value "+lit(a["quote"])+" .")
        ttl.append(u("#provenance")+" {\n"+"\n".join(prov)+"\n}")
        ttl.append(u("#pubinfo")+" { "+u()+" dct:creator "+lit("GPT-6.2Astra")+" ; dct:conformsTo <http://www.nanopub.org/nschema> . }")
        refs.extend(evidence);facts["id"]=uri;data.append(facts)
    require(data,"no comparisons specified")
    (out/"comparisons.trig").write_text("\n\n".join(ttl)+"\n",encoding="utf-8")
    dump(out/"comparisons.json",{"author":"GPT-6.2Astra","comparisons":data})
    rows=[(h(x["scope"]),h(x["reference"]+" · "+x["reference_value"]),h(x["comparison"]+" · "+x["comparison_value"]),
           h(x["difference"]+" "+x["unit"])," ".join(link(e) for e in x["evidence"][:2])) for x in data]
    html_page(out/"observations.html",plan["title"],html_table(("条件","参照组","比较组","比较组减参照组","测量出处"),rows),refs)
if __name__=="__main__":
    main(render)
