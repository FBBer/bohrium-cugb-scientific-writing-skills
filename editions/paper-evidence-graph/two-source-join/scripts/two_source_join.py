"""Answer a cross-paper question by joining directed, qualified edges to a common target."""
from itertools import product
import re
from xml.etree import ElementTree as ET
from edition_io import main, require, anchor
from sourcebook import dump, h, html_page, html_table, link

def mentions(text,label):
    pat=r"(?<![A-Za-z0-9])"+re.escape(label)+r"(?![A-Za-z0-9])" if re.search("[A-Za-z0-9]",label) else re.escape(label)
    return re.search(pat,text,re.I) is not None

def render(sources,plan,out):
    """Write an evidence-linked answer and a reusable directed GraphML file."""
    nodes={};refs=[];edges=[];ids=set()
    for n in plan["nodes"]:
        require(n["id"] and n["id"] not in nodes,"duplicate node id")
        nodes[n["id"]]=n
    def resolve(term):
        if term in nodes:return term
        hits=[i for i,n in nodes.items() if term.casefold() in [s.casefold() for s in [n["name"]]+n.get("aliases",[])]]
        require(len(hits)==1,f"ambiguous or missing entity {term!r}; supply the node ID")
        return hits[0]
    for relation in plan["edges"]:
        e={**relation,"from":resolve(relation["from"]),"to":resolve(relation["to"])}
        require(e["id"] not in ids,"duplicate edge id")
        require(e["polarity"] in ("positive","negative","uncertain"),"unrecognized polarity")
        require(bool(e["scope"].strip()) and bool(e["predicate"].strip()),"missing edge condition or predicate")
        a=anchor(sources,e["evidence"]); text=a["quote"]
        for i in ("from","to"):
            node=nodes[e[i]]
            require(any(mentions(text,t) for t in [node["name"]]+node.get("aliases",[])),f"missing entity in {e['id']}")
        require(e["surface"].strip() and e["surface"].casefold() in text.casefold(),"relation wording missing from the cited text")
        if e.get("scope_evidence"):
            sc=anchor(sources,e["scope_evidence"])
            require(sc["source"]==a["source"] and mentions(sc["quote"],e["scope"]),"scope passage missing or from another work")
            e["scope_evidence"]=sc;refs.append(sc)
        else:
            require(mentions(text,e["scope"]),"scope missing from the relation passage")
        if re.search(r"\b(?:did not|does not|never|no evidence of)\b|未发现|未检测到",e["surface"],re.I):
            require(e["polarity"]!="positive","negated relation cannot be positive")
        e["evidence"]=a;edges.append(e);refs.append(a);ids.add(e["id"])
    answers=[];body=[]
    for q in plan["questions"]:
        left,right=map(resolve,q["subjects"]);require(left!=right,"two different subjects needed")
        def matches(start,target):
            return [e for e in edges if (e["from"],e["to"],e["scope"],e["predicate"])==(start,target,q["scope"],q["predicate"])]
        result=[]
        for target in nodes:
            le,ri=matches(left,target),matches(right,target)
            if not le or not ri:continue
            pairs=[(a,b) for a,b in product(le,ri) if a["evidence"]["source"]!=b["evidence"]["source"]]
            if not pairs:continue
            positive=[(a,b) for a,b in pairs if a["polarity"]==b["polarity"]=="positive"]
            polarities={e["polarity"] for e in le+ri}
            status="supported" if positive and polarities=={"positive"} else "conflicted" if positive and "negative" in polarities else "qualified"
            result.append(dict(target=target,status=status,edge_ids=[e["id"] for e in le+ri],
                               paper_pairs=[[a["id"],b["id"]] for a,b in pairs]))
        answers.append({"question":q["question"],"scope":q["scope"],"results":result})
        supported=[nodes[r["target"]]["name"] for r in result if r["status"]=="supported"]
        body.append("<h2>"+h(q["question"])+"</h2><p>"+(h("、".join(supported)) if supported else "在给定条件下，两篇材料没有给出一致的肯定答案。")+"</p>")
        for r in result:
            tags={"supported":"两篇文献均支持","conflicted":"存在相反观测","qualified":"有否定或不确定记录"}
            body.append("<h3>"+h(nodes[r["target"]]["name"])+" · "+tags[r["status"]]+"</h3>")
            body.extend("<p>"+h(e["evidence"]["quote"])+" "+link(e["evidence"])+"</p>" for e in edges if e["id"] in r["edge_ids"])
    html_page(out/"answers.html",plan["title"],"".join(body),refs)
    dump(out/"graph.json",{"author":"GPT-6.2Astra","nodes":list(nodes.values()),"edges":edges,"answers":answers})
    ns="http://graphml.graphdrawing.org/xmlns";ET.register_namespace("",ns)
    def child(parent,tag,**attrs):return ET.SubElement(parent,"{"+ns+"}"+tag,attrs)
    root=ET.Element("{"+ns+"}graphml")
    for key,kind in (("label","node"),("type","node"),("predicate","edge"),("scope","edge"),("polarity","edge"),("source","edge"),("quote","edge")):
        child(root,"key",id=key,**{"for":kind,"attr.name":key,"attr.type":"string"})
    gx=child(root,"graph",id="papers",edgedefault="directed")
    for i,n in nodes.items():
        v=child(gx,"node",id=i)
        for k,val in (("label",n["name"]),("type",n["type"])):child(v,"data",key=k).text=val
    for e in edges:
        v=child(gx,"edge",id=e["id"],source=e["from"],target=e["to"])
        for k in ("predicate","scope","polarity"):child(v,"data",key=k).text=e[k]
        a=e["evidence"]
        child(v,"data",key="source").text=a["source"]+" · "+a["loc"]
        child(v,"data",key="quote").text=a["quote"]
    ET.ElementTree(root).write(out/"graph.graphml",encoding="utf-8",xml_declaration=True)
if __name__=="__main__":
    main(render)
