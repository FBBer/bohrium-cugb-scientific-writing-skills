"""Research graph queries preserve edge direction, evidence and explicit alias decisions."""
from collections import defaultdict,deque
from datetime import date
from sourcebook import dump,h,html_page,html_table,link,source_id,table

def produce(mode,sources,rows,plan,out,title):
    edges=[{'from':r['subject'],'to':r['object'],'relation':r['relation'],'source':r['anchors'],'id':r['id'],'scope':r.get('scope',''),'polarity':r.get('polarity','stated'),'date':r.get('date'),'until':r.get('until')} for r in rows]
    nodes={n for e in edges for n in (e['from'],e['to'])}
    q=plan.get('query',{}); subset=edges; other={}
    if mode=='evidence-paths':
        start,end=q['from'],q['to']; graph=defaultdict(list)
        for e in edges:graph[e['from']].append(e)
        parent={start:None};queue=deque([start])
        while queue:
            v=queue.popleft()
            if v==end:break
            for e in graph[v]:
                if e['to'] not in parent: parent[e['to']]=e;queue.append(e['to'])
        v=end;subset=[]
        if end in parent:
            while parent[v] is not None:
                edge=parent[v];subset.append(edge);v=edge['from']
            subset.reverse()
        other={'from':start,'to':end,'reachable':start in nodes and end in nodes and end in parent,'hops':len(subset)}
    elif mode=='local-atlas':
        v=q['node'];subset=[e for e in edges if v in (e['from'],e['to'])];other={'node':v,'incoming':sum(e['to']==v for e in subset),'outgoing':sum(e['from']==v for e in subset)}
    elif mode=='time-slice':
        point=date.fromisoformat(q['date']);subset=[];unknown=[]
        for e in edges:
            if not e['date']:unknown.append(e['id']);continue
            lo=date.fromisoformat(e['date']);hi=date.fromisoformat(e['until']) if e['until'] else None
            if hi and hi<lo:raise ValueError('Invalid validity interval.')
            if lo<=point and (hi is None or point<=hi):subset.append(e)
        other={'as_of':str(point),'undated':unknown}
    elif mode=='disagreement':
        groups=defaultdict(list)
        for e in edges:groups[(e['from'],e['relation'],e['to'],e['scope'])].append(e)
        subset=[e for v in groups.values() if {'positive','negative'}<={i['polarity'] for i in v} for e in v]
        other={'opposed_groups':len({(e['from'],e['relation'],e['to'],e['scope']) for e in subset})}
    elif mode=='alias-register':
        candidates=defaultdict(set);aliases=[]
        for r in rows:
            for name in r.get('aliases',[]):
                if not any(name.casefold() in a['quote'].casefold() for a in r['anchors']):raise ValueError('Alias missing from excerpt.')
                candidates[name.casefold()].add(r['subject'])
        for alias,names in sorted(candidates.items()):aliases.append({'alias':alias,'entities':sorted(names),'ambiguous':len(names)>1})
        other={'aliases':aliases}
    elif mode=='components':
        adjacency=defaultdict(set)
        for e in edges:adjacency[e['from']].add(e['to']);adjacency[e['to']].add(e['from'])
        unseen=set(nodes); groups=[]
        while unseen:
            group={min(unseen)};queue=deque(group)
            while queue:
                for v in adjacency[queue.popleft()]-group:group.add(v);queue.append(v)
            unseen-=group;groups.append(sorted(group))
        other={'weak_components':groups,'component_count':len(groups)}
    else:raise ValueError(mode)
    dump(out/'graph-query.json',{'query':q,**other,'edges':subset})
    table(out/'edges.tsv',['from','relation','to','scope','date','evidence'],[[e['from'],e['relation'],e['to'],e['scope'],e['date'],' | '.join(source_id(a) for a in e['source'])] for e in subset])
    cols=['起点','关系','终点','出处'];matrix=[[h(e['from']),h(e['relation']),h(e['to']),' · '.join(link(a) for a in e['source'])] for e in subset]
    if mode=='evidence-paths':
        body='<ol>'+''.join('<li>'+r[0]+' → '+r[2]+' <b>'+r[1]+'</b> '+r[3]+'</li>' for r in matrix)+'</ol>' if subset else '<p>'+('同一节点。' if other['reachable'] else '没有找到有证据的有向路径。')+'</p>'
    else:
        body=html_table(cols,matrix)
        if mode=='alias-register':body=html_table(['别名','候选实体'],[[h(a['alias']),h(' / '.join(a['entities']))] for a in other['aliases']])+body
        if mode=='components':body=''.join('<p>'+h(' · '.join(g))+'</p>' for g in other['weak_components'])+body
        if mode=='time-slice':body='<p>'+h(q['date'])+'</p>'+body
    html_page(out/'graph.html',title,body,[a for e in subset for a in e['source']],'timeline' if mode=='evidence-paths' else 'ledger')
    from xml.etree import ElementTree as ET
    ns='http://graphml.graphdrawing.org/xmlns';gml=ET.Element('graphml',xmlns=ns)
    for name,kind in [('name','node'),('relation','edge'),('evidence','edge')]:
        ET.SubElement(gml,'key',{'id':name,'for':kind,'attr.name':name,'attr.type':'string'})
    gg=ET.SubElement(gml,'graph',edgedefault='directed',id='G');ids={}
    for name in sorted({n for e in subset for n in (e['from'],e['to'])}):
        nid='n'+str(len(ids));ids[name]=nid;node=ET.SubElement(gg,'node',id=nid);ET.SubElement(node,'data',key='name').text=name
    for j,e in enumerate(subset):
        ed=ET.SubElement(gg,'edge',id='e'+str(j),source=ids[e['from']],target=ids[e['to']]);ET.SubElement(ed,'data',key='relation').text=e['relation']
        ET.SubElement(ed,'data',key='evidence').text=' | '.join(source_id(a)+': '+a['quote'] for a in e['source'])
    ET.ElementTree(gml).write(out/'selected.graphml',encoding='utf-8',xml_declaration=True)
    return ['graph-query.json','edges.tsv','graph.html','selected.graphml']
