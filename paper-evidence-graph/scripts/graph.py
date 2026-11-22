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
        return "(?:" + "|".join(re.escape(t) for t in sorted(terms, key=lambda t: (-len(t), t)) if t) + ")"

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
        r"(?<![A-Za-z0-9_])(?P<subject>" + names(subject) + r")(?![A-Za-z0-9_])"
        r"\s*(?P<qualifier>(?:(?!\b(?:and|but|whereas)\b|但是|然而|但)[^.,;!?，。；！？]){0,100}?)"
        r"(?P<verb>" + choices(phrases) + r")"
        r"\s*(?:(?:the|an?|this|that)\s+|该|此)?" + names(target) + r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )


def qualified_polarity(phrase):
    """Distinguish an observed relation from a denial or a statement of possibility."""
    phrase = phrase.strip().casefold().replace("’", "'")
    if re.search(r"[\u3400-\u9fff]", phrase):
        if re.search(r"可能|也许|或许|似乎|未必|不一定|不无|不能排除|难以|据称|很少", phrase):
            return "uncertain"
        phrase = re.sub(r"不仅|不但|不只", "", phrase)
        tokens = re.findall(r"并没有|并未|并非|并不|未曾|从未|没有|未|不|实际上|实际|确实|曾经|曾|被|直接", phrase)
        if "".join(tokens) != phrase:
            return "needs_review"
        negatives = sum(t in {"并没有","并未","并非","并不","未曾","从未","没有","未","不"} for t in tokens)
    else:
        phrase = re.sub(r"n't\b", " not", phrase)
        phrase = re.sub(r"\bnot\s+(?:only|just|merely)\b", "", phrase)
        if re.search(r"\b(?:may|might|can|could|would|should|possibly|probably|likely|unlikely|possible|impossible|"
                     r"apparently|reportedly|allegedly|rarely|hardly|perhaps|seems?|seemed|potentially)\b"
                     r"|\bnot\s+(?:always|necessarily|fully|consistently)\b", phrase):
            return "uncertain"
        tokens = phrase.split()
        auxiliaries = {"is","are","was","were","be","been","being","do","does","did","have","has","had"}
        neutral = {"actually","really","also","only","just","merely","previously","recently","directly",
                   "indeed","explicitly","successfully","experimentally","ever",
                   "measurably","detectably","significantly","statistically","materially"}
        allowed = auxiliaries | neutral | {"not", "never"}
        if any(t not in allowed for t in tokens):
            return "needs_review"
        negatives = sum(t in {"not","never"} for t in tokens)
    if negatives > 1:
        return "needs_review"
    return "negative" if negatives else "positive"


def passage_polarity(passage, match):
    lead = re.split(r"[.!?;，。；！？,]|\b(?:and|but|whereas)\b|但是|然而|但",
                    passage[:match.start("subject")], flags=re.I)[-1]
    if re.search(r"\b(?:if|whether|hypothes\w*|assum\w*|possibly|perhaps)\b"
                 r"|\bno\s+(?:reliable\s+)?evidence\b"
                 r"|\bnot\s+(?:yet\s+)?(?:shown|established|demonstrated|clear|known|certain)\b"
                 r"|如果|假设|是否|尚未证实|不能确认|无证据|没有证据|猜测", lead, re.I):
        return "uncertain"
    return qualified_polarity(match.group("qualifier"))


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
                passage_polarity(passage, m)
                for m in pattern.finditer(passage)
                if any(lo <= m.start("verb") and m.end("verb") <= hi for lo, hi in excerpts)
            }
            if signs and signs != {edge["polarity"]}:
                issues.append({"edge":edge["predicate"], "evidence":ref, "source_readings":sorted(signs),
                               "issues":["this passage does not establish the stated direct relation"]})
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

def query_paths(graph, spec, refs):
    """Trace cited edges in either direction, retaining the relation as the source states it."""
    steps = spec["steps"]
    if not isinstance(steps,list) or not 1 <= len(steps) <= 6:
        raise ValueError("a path query needs between one and six ordered steps")
    nodes = {n["id"]:n for n in graph["nodes"]}
    policy = spec.get("scope_policy", "any")
    if policy not in {"any", "same"}:
        raise ValueError("scope_policy must be any or same")
    adjacent = {"out": collections.defaultdict(list), "in": collections.defaultdict(list)}
    for edge in graph["edges"]:
        adjacent["out"][edge["source"]].append((edge["target"], edge))
        adjacent["in"][edge["target"]].append((edge["source"], edge))
    for step in steps:
        if not isinstance(step,dict) or not step.get("predicate") or set(step) - {"predicate","strength","polarity","scope","target_type","direction"}:
            raise ValueError("each path step needs a predicate and supported qualifiers")
        if step.get("direction", "out") not in {"out", "in"}:
            raise ValueError("a step direction must be out or in")
    start, finish = (refs.get(spec.get(key),spec.get(key)) for key in ("from","to"))
    if start is None:
        raise ValueError("supply the starting entity for a directed path query")
    paths = [([start], [])] if start in nodes else []
    for step in steps:
        qualified = {"strength":"direct","polarity":"positive",**step}
        target_type = qualified.pop("target_type",None)
        direction = qualified.pop("direction", "out")
        extended = []
        for ids, route in paths:
            for next_id, edge in adjacent[direction][ids[-1]]:
                if next_id in ids or (target_type and nodes[next_id]["type"] != target_type):
                    continue
                if policy == "same" and route and edge["scope"] != route[0]["scope"]:
                    continue
                if all(edge.get(k) == v for k, v in qualified.items()):
                    extended.append((ids + [next_id], route + [edge]))
        paths = extended
    if finish is not None:
        paths = [(ids,edges) for ids,edges in paths if ids[-1]==finish]
    route_rows = []
    for ids, edges in paths:
        hops = []
        for index, edge in enumerate(edges):
            hop = {k:edge[k] for k in ("source","target","predicate","scope","strength","polarity","evidence")}
            hops.append({**hop, "edge":edge["id"], "direction":steps[index].get("direction","out"),
                         "traversed_from":ids[index], "traversed_to":ids[index+1]})
        route_rows.append({"nodes":ids, "steps":hops})
    return {"question":spec["question"], "filters":{k:v for k,v in spec.items() if k!="question"},
            "paths":route_rows, "nodes":sorted({node for ids,_ in paths for node in ids}),
            "edges":list(dict.fromkeys(edge["id"] for _,edges in paths for edge in edges)),
            "evidence":unique([ev for _,edges in paths for e in edges for ev in e["evidence"]]),
            "status":"supported_matches" if paths else "no_supported_match_in_sources"}


def query(graph,spec,refs):
    if "steps" in spec:
        return query_paths(graph,spec,refs)
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
