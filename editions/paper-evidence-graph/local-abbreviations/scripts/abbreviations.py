"""Resolve short names using definitions in each paper before building a directed graph."""
from collections import defaultdict
import re
from xml.etree import ElementTree as ET
from edition_io import main,anchor,require
from sourcebook import dump,h,html_page,html_table,link
def present(text,term):
    pattern=r"(?<![A-Za-z0-9])"+re.escape(term)+r"(?![A-Za-z0-9])" if re.search("[A-Za-z0-9]",term) else re.escape(term)
    return re.search(pattern,text,re.I) is not None
def render(sources,plan,out):
    nodes={};registry=defaultdict(set);origins=defaultdict(list);refs=[]
    for n in plan["nodes"]:
        require(n["id"] and n["id"] not in nodes,"duplicate entity");nodes[n["id"]]=n
    for x in plan["definitions"]:
        a=anchor(sources,x["evidence"]);node=nodes[x["node"]];term=x["short"]
        require(present(a["quote"],node["label"]) and present(a["quote"],term),"definition must quote short name and expansion together")
        reg=(a["source"],term.casefold())
        registry[reg].add(node["id"]);origins[(reg,node["id"])].append(a);refs.append(a)
    byname=defaultdict(set)
    for k,n in nodes.items():byname[n["label"].casefold()].add(k)
    edges=[];unresolved=[];ids=set()
    for e in plan["edges"]:
        a=anchor(sources,e["evidence"]);refs.append(a);key=e["id"]
        require(key not in ids,"duplicate edge");ids.add(key)
        ends=[];defs=[]
        for term in (e["from"],e["to"]):
            require(present(a["quote"],term),"mention missing from evidence")
            reg=(a["source"],term.casefold());candidates=registry[reg]|byname[term.casefold()]
            if len(candidates)!=1:
                unresolved.append(dict(edge=key,term=term,file=a["source"],candidates=sorted(candidates),evidence=a));break
            node=next(iter(candidates));ends.append(node);defs.extend(origins[(reg,node)])
        if len(ends)!=2:continue
        require(e["surface"] and e["surface"].casefold() in a["quote"].casefold(),"predicate wording missing")
        require(e["polarity"] in ("positive","negative","uncertain"),"unknown polarity")
        edges.append(dict(id=key,subject=ends[0],object=ends[1],predicate=e["predicate"],polarity=e["polarity"],scope=e.get("scope",""),evidence=a,definitions=defs))
    answers=[];body=[]
    for q in plan.get("questions",[]):
        hits=[e for e in edges if e["subject"]==q["subject"] and e["predicate"]==q["predicate"] and (not q.get("scope") or e["scope"]==q["scope"])]
        answers.append(dict(question=q["text"],edge_ids=[v["id"] for v in hits]))
        body.append("<h2>"+h(q["text"])+"</h2>")
        for v in hits:
            body.append("<p>"+h(nodes[v["object"]]["label"])+" · "+h({"positive":"有记录","negative":"否定记录","uncertain":"不确定"}[v["polarity"]])+" "+link(v["evidence"])+"</p>")
        if not hits:body.append("<p>没有找到符合这些条件的有向记录。</p>")
    body.append(html_table(("文献","缩写","该文中的全称"),[(h(file),h(term),h(" / ".join(nodes[k]["label"] for k in sorted(values)))) for (file,term),values in registry.items() if values]))
    if unresolved:body.append("<p>待辨认的关系："+h("、".join(r["edge"] for r in unresolved))+"。</p>")
    html_page(out/"graph.html",plan["title"],"".join(body),refs)
    dump(out/"graph.json",dict(author="GPT-6.2Astra",nodes=list(nodes.values()),edges=edges,unresolved=unresolved,answers=answers))
    ns="http://graphml.graphdrawing.org/xmlns";ET.register_namespace("",ns)
    def add(t,tag,**attr):return ET.SubElement(t,"{"+ns+"}"+tag,attr)
    root=ET.Element("{"+ns+"}graphml")
    for k,entity in (("label","node"),("type","node"),("relation","edge"),("evidence","edge"),("scope","edge"),("polarity","edge")):
        add(root,"key",id=k,**{"for":entity,"attr.name":k,"attr.type":"string"})
    g=add(root,"graph",id="papers",edgedefault="directed")
    for id,n in nodes.items():
        v=add(g,"node",id=id)
        for k in ("label","type"):add(v,"data",key=k).text=n[k]
    for e in edges:
        v=add(g,"edge",id=e["id"],source=e["subject"],target=e["object"])
        for k,val in (("relation",e["predicate"]),("scope",e["scope"]),("polarity",e["polarity"]),("evidence",e["evidence"]["source"]+" "+e["evidence"]["loc"]+" "+e["evidence"]["quote"])):
            add(v,"data",key=k).text=val
    ET.ElementTree(root).write(out/"graph.graphml",encoding="utf-8",xml_declaration=True)
if __name__=="__main__":main(render)
