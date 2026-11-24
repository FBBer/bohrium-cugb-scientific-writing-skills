"""Portable nanopublications with stable named graphs, provenance and edition-specific assertions."""
import hashlib,json,re
from decimal import Decimal
from urllib.parse import quote
from sourcebook import dump,h,html_page,html_table,link,source_id,table
NP='http://www.nanopub.org/nschema#';PROV='http://www.w3.org/ns/prov#';RDF='http://www.w3.org/1999/02/22-rdf-syntax-ns#';XSD='http://www.w3.org/2001/XMLSchema#';DCT='http://purl.org/dc/terms/'
def iri(s):return '<'+s+'>'
def literal(s):return json.dumps(str(s),ensure_ascii=False)
def term(s):return iri('urn:research:term:'+quote(str(s),safe=''))
def produce(mode,sources,rows,plan,out,title):
    quads=[]; records=[]; seen={r['id']:r for r in rows}
    def add(s,p,o,g):quads.append(' '.join([s,iri(p),o,g,'.']))
    def base(r):
        v=json.dumps([mode,r['id'],r['subject'],r['relation'],r['object'],r.get('value'),r.get('unit'),r.get('conditions'),r.get('revises'),[a['ref'] for a in r['anchors']]],ensure_ascii=False,separators=(',',':'))
        return 'urn:research:nanopub:'+hashlib.sha256(v.encode()).hexdigest()
    ids={r['id']:base(r) for r in rows}
    if mode=='revision-history':
        for r in rows:
            p=r.get('revises');used={r['id']}
            while p:
                if p not in seen or p in used:raise ValueError('Revision must reference an existing earlier assertion without a cycle.')
                used.add(p);p=seen[p].get('revises')
    for r in rows:
        u=ids[r['id']];n=iri(u);head=iri(u+':head');a=iri(u+':assertion');pv=iri(u+':provenance');pub=iri(u+':pubinfo')
        add(n,RDF+'type',iri(NP+'Nanopublication'),head)
        for pred,obj in [('hasAssertion',a),('hasProvenance',pv),('hasPublicationInfo',pub)]:add(n,NP+pred,obj,head)
        sub=term(r['subject']);pred='urn:research:relation:'+quote(r['relation'],safe='');add(sub,pred,term(r['object']),a)
        add(n,DCT+'identifier',literal(r['id']),pub);add(n,DCT+'title',literal(r.get('text') or r['subject']),pub)
        for anchor in r['anchors']:
            src=iri('urn:research:excerpt:'+anchor['ref'])
            add(a,PROV+'wasDerivedFrom',src,pv);add(src,DCT+'source',literal(source_id(anchor)),pv);add(src,RDF+'value',literal(anchor['quote']),pv)
        if mode=='measured-claims':
            raw=str(r['value']); val=Decimal(raw); unit=str(r['unit'])
            if not val.is_finite() or not any(unit in x['quote'] and any(Decimal(z)==val for z in re.findall(r'[-+]?\d+(?:\.\d+)?',x['quote'])) for x in r['anchors']):raise ValueError('Measurement or unit missing from excerpt')
            add(sub,'urn:research:value',literal(format(val,'f'))+'^^'+iri(XSD+'decimal'),a); add(sub,'urn:research:unit',literal(unit),a)
        elif mode=='revision-history' and r.get('revises'):
            add(n,PROV+'wasRevisionOf',iri(ids[r['revises']]),pub)
        elif mode=='scoped-claims':
            for cond in r['conditions']:
                if not any(cond.casefold() in x['quote'].casefold() for x in r['anchors']):raise ValueError('Condition not present in evidence')
                add(a,'urn:research:condition',literal(cond),pv)
        elif mode=='source-bundles':
            if len({x['source'] for x in r['anchors']})<2:raise ValueError('This bundle requires at least two distinct source documents.')
            for anchor,role in zip(r['anchors'],r['roles'],strict=True):
                if role not in {'supports','qualifies','contrasts'}: raise ValueError('Unknown source role')
                add(iri('urn:research:excerpt:'+anchor['ref']),'urn:research:evidenceRole',literal(role),pv)
        elif mode not in {'quoted-statements','revision-history'}:raise ValueError(mode)
        records.append({'id':r['id'],'nanopub':u,'statement':[r['subject'],r['relation'],r['object']],'evidence':r['anchors'],'conditions':r.get('conditions',[]),'value':r.get('value'),'unit':r.get('unit'),'revises':r.get('revises'),'roles':r.get('roles',[])})
    (out/'claims.nq').write_text('\n'.join(quads)+'\n',encoding='utf-8');dump(out/'claims.json',records)
    cells=[[h(x['id']),h(' · '.join(x['statement'])),h(' / '.join(map(str,x['conditions']+x['roles'])) or str(x['revises'] or '') or ' '.join(str(i) for i in (x['value'],x['unit']) if i is not None)),' · '.join(link(a) for a in x['evidence'])] for x in records]
    if mode=='revision-history':
        body='<ol>'+''.join('<li><b>'+h(x['id'])+'</b> '+h(' · '.join(x['statement']))+' '+('← '+h(x['revises']) if x['revises'] else '')+'</li>' for x in records)+'</ol>'
    else:body=html_table(['断言','主语 · 关系 · 宾语','限定 / 版本','出处'],cells)
    html_page(out/'claims.html',title,body,[a for x in records for a in x['evidence']],'timeline' if mode=='revision-history' else 'ledger')
    return ['claims.nq','claims.json','claims.html']
