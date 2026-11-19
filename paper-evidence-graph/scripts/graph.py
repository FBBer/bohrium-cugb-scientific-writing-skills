"""Build a provenance-preserving directed multigraph and run auditable case-specific queries."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from casework import read,write,atomic_text,check_evidence

def stable(prefix,value):
    return prefix+hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:17]

def relation_mentions(edge, subject, target):
    """Match a plainly worded relation between these named endpoints in one clause."""
    def choices(terms):
        return "(?:" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True) if t) + ")"

    def names(node):
        return choices({node["label"], *node.get("aliases", [])})

    phrases = {str(edge.get(k) or "").replace("_", " ").strip()
               for k in ("predicate", "display_predicate")} - {""}
    if any(re.search(r"\b(?:not|never|without|no)\b|^(?:并未|没有|未|不|非)", p, re.I) for p in phrases):
        return None
    verb_forms = ("use uses used", "compare compares compared", "reduce reduces reduced",
                  "improve improves improved", "increase increases increased", "change changes changed",
                  "support supports supported", "predict predicts predicted", "evaluate evaluates evaluated")
    for phrase in tuple(phrases):
        head, _, rest = phrase.partition(" ")
        for forms in verb_forms:
            if head.casefold() in forms.split():
                phrases.update((word + " " + rest).strip() for word in forms.split())
    return re.compile(
        r"(?:^|(?<=[.,;!?，。；！？])|\b(?:and|but|whereas)\s+|但是|然而|但)\s*"
        r"(?:(?:the|an?|this|that)\s+|该|此)?" + names(subject) +
        r"\s*(?:(?:was|were|is|are|do|did|does|has|have|had)\s+)?"
        r"(?P<neg>(?:(?:was|were|is|are|do|did|does|has|have|had)n['’]t|not|never)\s+"
        r"|并没有|并未|没有|并非|并不|未曾|从未|未|不)?"
        r"(?:been\s+|被)?(?P<verb>" + choices(phrases) + r")"
        r"\s*(?:(?:the|an?|this|that)\s+|该|此)?" + names(target) + r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )


def check_relation_polarity(edges, nodes, sources, issues):
    """Keep compatible evidence, including evidence imported from older graph files."""
    retained = []
    for edge in edges:
        if edge["strength"] != "direct" or edge["polarity"] not in {"positive", "negative"}:
            retained.append(edge)
            continue
        pattern = relation_mentions(edge, nodes[edge["source"]], nodes[edge["target"]])
        if pattern is None:
            retained.append(edge)
            continue
        evidence = []
        for ref in edge["evidence"]:
            quote = ref["quote"]
            passage = sources.get(ref["id"], quote)
            excerpts = [m.span() for m in re.finditer(re.escape(quote), passage)]
            signs = {
                "negative" if m.group("neg") else "positive"
                for m in pattern.finditer(passage)
                if any(lo <= m.start("verb") and m.end("verb") <= hi for lo, hi in excerpts)
            }
            if len(signs) == 1 and edge["polarity"] not in signs:
                issues.append({"edge":edge["predicate"], "evidence":ref,
                               "issues":["explicit source polarity conflicts with this relation"]})
            else:
                evidence.append(ref)
        if evidence:
            retained.append({**edge, "evidence":evidence})
    return retained


def dataset(index,plan,previous=None):
    graph=previous or {"nodes":[],"edges":[]}
    nodes={n["id"]:dict(n) for n in graph["nodes"]};edges={e["id"]:dict(e) for e in graph["edges"]}
    refs={};notes=[];source_files={s["id"]:s["source"] for s in index["sources"]}
    for n in plan.get("nodes",[]):
        local=n.get("key"); ev=n.get("evidence",[])
        err=check_evidence(ev,index["sources"])
        if not all(n.get(x) for x in ("key","type","label","scope")) or not ev: err.append("missing typed, scoped or grounded identity")
        if local in refs: err.append("duplicate local key")
        if err: notes.append({"node":local,"issues":err});continue
        # An unmerged ID includes document, entity sense and type. Aliases alone never merge objects.
        sid=stable("n",[n["type"],n["scope"],n["label"],n.get("document",source_files[ev[0]["id"]])])
        existing=n.get("same_as")
        if existing:
            existing=refs.get(existing,existing)
            if existing not in nodes or nodes[existing]["type"]!=n["type"] or not n.get("merge_reason"):
                notes.append({"node":local,"issues":["unverified alignment"],"candidate":existing})
            else: sid=existing
        refs[local]=sid
        if sid in nodes:
            old=nodes[sid];old["aliases"]=sorted(set(old.get("aliases",[])+n.get("aliases",[])+[n["label"]])-{old["label"]})
            old["evidence"]=unique(old["evidence"]+ev)
            old["members"]=unique(old.get("members",[])+[{"key":local,"document":n.get("document",source_files[ev[0]["id"]])}])
            if n.get("merge_reason"): old["alignments"]=list(dict.fromkeys(old.get("alignments",[])+[n["merge_reason"]]))
        else: nodes[sid]={**n,"id":sid,"members":[{"key":local,"document":n.get("document",source_files[ev[0]["id"]])}]}
    for e in plan.get("edges",[]):
        a=refs.get(e.get("source"),e.get("source"));b=refs.get(e.get("target"),e.get("target"))
        ev=e.get("evidence",[]);err=check_evidence(ev,index["sources"])
        if a not in nodes or b not in nodes: err.append("relation endpoint missing")
        if not ev or not all(e.get(k) for k in ("predicate","scope","strength","polarity")): err.append("missing qualified relation or evidence")
        if e.get("strength") not in {"direct","inference","quoted"}: err.append("unknown support type")
        if e.get("polarity") not in {"positive","negative","uncertain"}: err.append("unknown polarity")
        if err: notes.append({"edge":e.get("predicate"),"issues":err});continue
        sid=stable("e",[a,e["predicate"],b,e["scope"],e["polarity"],e["strength"]])
        edges[sid]={**e,"id":sid,"source":a,"target":b,"evidence":unique(edges.get(sid,{}).get("evidence",[])+ev)}
    texts = {s["id"]: s["text"] for s in index["sources"]}
    grounded = check_relation_polarity(edges.values(), nodes, texts, notes)
    return {"nodes":list(nodes.values()),"edges":grounded,"issues":notes}, refs

def unique(rows):
    return list({json.dumps(r,sort_keys=True,ensure_ascii=False):r for r in rows}.values())

def query(graph,spec,refs):
    nodes={n["id"]:n for n in graph["nodes"]}; hits=[]
    for e in graph["edges"]:
        fields=spec.get("where",{})
        if any(e.get(k)!=refs.get(v,v) if k in {"source","target"} else e.get(k)!=v for k,v in fields.items()): continue
        if spec.get("source_type") and nodes[e["source"]]["type"]!=spec["source_type"]: continue
        if spec.get("target_type") and nodes[e["target"]]["type"]!=spec["target_type"]: continue
        hits.append(e)
    return {"question":spec["question"],"filters":{k:v for k,v in spec.items() if k!="question"},"edges":[e["id"] for e in hits],
            "nodes":sorted({e[x] for e in hits for x in ("source","target")}),"evidence":unique([ev for e in hits for ev in e["evidence"]]),
            "status":"supported_matches" if hits else "no_supported_match_in_sources"}

def edition_anchors(index,plan,previous):
    prior=(previous or {}).get("anchors",{})
    by_document=collections.defaultdict(list)
    for line in index["sources"]:
        by_document[line["source"]].append((line["location"],line["text"]))
    versions={name:stable("v",sorted(rows)) for name,rows in by_document.items()}
    remap={};anchors={};sources=[]
    for line in index["sources"]:
        old=line["id"]
        record={"source":line["source"],"location":line["location"],"edition":versions[line["source"]],
                "case_id":index.get("case_id")}
        key=old if old not in prior or prior[old]==record else old+"-"+stable("v",record)[1:]
        remap[old]=key
        anchors[key]=record
        sources.append({**line,"id":key})
    updated=dict(plan)
    for collection in ("nodes","edges"):
        updated[collection]=[{**r,"evidence":[{**e,"id":remap.get(e.get("id"),e.get("id"))} for e in r.get("evidence",[])]}
                             for r in plan.get(collection,[])]
    return {**index,"sources":sources},updated,{**prior,**anchors}

def export(index,plan,out,previous=None):
    index,plan,anchors=edition_anchors(index,plan,previous)
    graph,refs=dataset(index,plan,previous)
    graph["anchors"]=anchors
    answers=[query(graph,q,refs) for q in plan.get("queries",[])]
    write(out/"graph.json",graph);write(out/"queries.json",answers)
    ns="http://graphml.graphdrawing.org/xmlns";ET.register_namespace("",ns)
    el=lambda tag:"{"+ns+"}"+tag
    root=ET.Element(el("graphml"))
    for k in ("label","details"): ET.SubElement(root,el("key"),{"id":k,"for":"all","attr.name":k,"attr.type":"string"})
    g=ET.SubElement(root,el("graph"),{"id":"literature","edgedefault":"directed"})
    for kind,rows in (("node",graph["nodes"]),("edge",graph["edges"])):
        for item in rows:
            attrs={"id":item["id"]}
            if kind=="edge":attrs.update(source=item["source"],target=item["target"])
            entry=ET.SubElement(g,el(kind),attrs)
            ET.SubElement(entry,el("data"),{"key":"label"}).text=item.get("label",item.get("predicate"))
            ET.SubElement(entry,el("data"),{"key":"details"}).text=json.dumps(item,ensure_ascii=False,sort_keys=True)
    atomic_text(out/"graph.graphml",ET.tostring(root,encoding="unicode")+"\n")
    from diagram import render
    manifest = out/"figures.json"
    old_figures = read(manifest).get("files", []) if manifest.exists() else []
    figures = render(graph, answers, out/"figures")
    for name in set(old_figures) - set(figures["files"]):
        if re.fullmatch(r"query-\d+-\d+\.(?:svg|pdf|png)", name):
            (out/"figures"/name).unlink(missing_ok=True)
    write(manifest, figures)
    return graph,answers
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("index");p.add_argument("plan");p.add_argument("out",type=Path);p.add_argument("--previous")
    a=p.parse_args();g,q=export(read(a.index),read(a.plan),a.out,read(a.previous) if a.previous else None);print(len(g["nodes"]),"nodes,",len(g["edges"]),"edges,",len(q),"queries")
