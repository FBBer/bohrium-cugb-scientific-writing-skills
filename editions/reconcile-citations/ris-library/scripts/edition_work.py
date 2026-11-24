"""Citation registers with exact mention locations and reversible bibliographic exports."""
import re
from collections import defaultdict
from sourcebook import dump,h,html_page,html_table,link,source_id,table
DOI=re.compile(r'(?i)10\.\d{4,9}/[-._;()/:A-Z0-9]+')
KEY=re.compile(r'(?<![\w@])@([\w:./\-]+)|\\(?:cite\w*)\s*(?:\[[^\]]*\]\s*)*\{([^{}]+)\}')
def normaldoi(raw):
    s=raw.strip().rstrip('.,;:').lower()
    while s.endswith(')') and s.count(')')>s.count('('):s=s[:-1]
    return s
def produce(mode,sources,rows,plan,out,title):
    refs={r['key']:r for r in rows}
    if len(refs)!=len(rows):raise ValueError('Bibliography keys must be unique.')
    occur=defaultdict(list)
    for s in sources.rows:
        if s['source'] in plan.get('bibliographies',[]):continue
        for m in KEY.finditer(s['text']):
            for key in (m[1] or m[2]).split(','):
                k=key.strip().rstrip('.,;');occur[k].append({'source':s['source'],'loc':s['loc'],'quote':s['text']})
    anchors=[a for r in rows for a in r['anchors']]
    if mode=='doi-families':
        groups=defaultdict(list);missing=[]
        for k,v in refs.items():
            mt=DOI.search(v['anchors'][0]['quote'])
            if mt:groups[normaldoi(mt[0])].append(k)
            else:missing.append(k)
        pairs=[{'doi':d,'keys':keys,'same_identifier':len(keys)>1} for d,keys in sorted(groups.items())]
        dump(out/'doi-groups.json',{'identifiers':pairs,'without_doi':missing,'related_versions':plan.get('related_versions',[])})
        body=html_table(['DOI','本地引用键'],[[h(v['doi']),h(' · '.join(v['keys']))] for v in pairs])
        html_page(out/'bibliography.html',title,body,anchors);return ['doi-groups.json','bibliography.html']
    if mode=='backlink-index':
        seen={k:{'known':k in refs,'mentions':v} for k,v in occur.items()};unmentioned=sorted(refs.keys()-occur.keys())
        dump(out/'citation-backlinks.json',{'citations':seen,'unmentioned':unmentioned})
        body=''.join('<section><h2>'+h(k)+'</h2>'+''.join('<p><b>'+h(s['source']+' '+s['loc'])+'</b> '+h(s['quote'])+'</p>' for s in v)+'</section>' for k,v in occur.items())
        html_page(out/'backlinks.html',title,body,anchors,'cards');return ['citation-backlinks.json','backlinks.html']
    if mode=='numbered-crosswalk':
        order=list(occur);index={k:i+1 for i,k in enumerate(order)}
        table(out/'crosswalk.tsv',['number','key','first_location','resolved'],[[i,k,source_id(occur[k][0]),k in refs] for k,i in index.items()])
        lines=[f'[{i}] '+(refs[k].get('text') or refs[k]['anchors'][0]['quote'] if k in refs else k+' [source missing]') for k,i in index.items()]
        (out/'ordered-references.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8');return ['crosswalk.tsv','ordered-references.md']
    if mode=='ris-library':
        lines=[]; cross=[]
        for k,r in refs.items():
            fields=[('TY',r.get('type','JOUR')),('ID',k),('TI',r['title'])]+[('AU',s) for s in r.get('authors',[])]+[('PY',r.get('year',''))]
            mt=DOI.search(r['anchors'][0]['quote'])
            if mt:fields.append(('DO',normaldoi(mt[0])))
            fields.append(('N1',source_id(r['anchors'][0])))
            for k1,v in fields:
                if str(v).strip():lines.append(k1+'  - '+str(v).replace('\n',' '))
            lines+=['ER  - ',''];cross.append([k,r['title'],source_id(r['anchors'][0])])
        (out/'library.ris').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        table(out/'reference-sources.tsv',['id','title','location'],cross);return ['library.ris','reference-sources.tsv']
    if mode=='claim-citation':
        ledger=[]
        for r in rows:
            for cite in r.get('supports',[]):
                if cite not in refs: raise ValueError('Unknown support key '+cite)
                ledger.append([r['key'],cite,r['anchors'][0]['quote'],refs[cite]['anchors'][0]['quote'],r.get('scope','')])
        table(out/'claim-to-source.tsv',['claim','source','claim excerpt','reference excerpt','scope'],ledger)
        html_page(out/'claim-map.html',title,html_table(['论断','引用键','原句','出处','适用条件'],[[h(x) for x in v] for v in ledger]),anchors);return ['claim-to-source.tsv','claim-map.html']
    raise ValueError(mode)
