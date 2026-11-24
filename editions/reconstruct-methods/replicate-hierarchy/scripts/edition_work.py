"""Build editable methods prose and a concrete experiment-specific reproducibility artifact."""
import json
from collections import defaultdict
from decimal import Decimal
from sourcebook import dump,h,html_page,html_table,link,source_id,table

def produce(mode,sources,rows,plan,out,title):
    anchors=[a for r in rows for a in r['anchors']]; paras=[]; grid=[]; extra=[]
    for r in rows:
        if not r.get('text','').strip():raise ValueError('Supply the editable methods paragraph.')
        paras.append((r.get('section','Methods'),r['text'],r['anchors']))
    if mode=='replicate-hierarchy':
        groups=defaultdict(lambda:defaultdict(set)); seen={}
        for r in rows:
            run=r['run'];triple=(r['condition'],r['unit_id'],str(r['repeat']))
            if run in seen and seen[run]!=triple:raise ValueError('Conflicting assignment for run '+run)
            seen[run]=triple;groups[triple[0]][triple[1]].add(triple[2])
        heads=['condition','independent units','observations','by unit']
        for cond,units in groups.items():grid.append([cond,len(units),sum(len(x) for x in units.values()),', '.join(f'{k} ({len(v)})' for k,v in units.items())])
    elif mode=='parameter-overrides':
        master=plan.get('defaults',{}); registry={}
        for r in rows:
            name=r['run']
            if name in registry:raise ValueError('Duplicate run configuration.')
            cfg={**master,**r['settings']};registry[name]={'parameters':cfg,'overridden':sorted(r['settings'].keys() & master.keys()),'location':source_id(r['anchors'][0])}
            for key,value in cfg.items():grid.append([name,key,str(value),'explicit' if key in r['settings'] else 'shared',source_id(r['anchors'][0])])
        dump(out/'run-configs.json',registry);extra=['run-configs.json'];heads=['run','parameter','value','origin','reference']
    elif mode=='sample-flow':
        heads=['stage','entered','excluded','retained','reason','reference']
        for r in rows:
            n,k=r['entered'],r['excluded']
            if type(n)!=int or type(k)!=int or not 0<=k<=n:raise ValueError('Invalid sample counts.')
            grid.append([r['stage'],n,k,n-k,r['reason'],source_id(r['anchors'][0])])
    elif mode=='metric-definitions':
        heads=['metric','numerator','denominator','calculated','unit','reference']
        for r in rows:
            top,btm=Decimal(str(r['numerator'])),Decimal(str(r['denominator']))
            if not btm:raise ValueError('Zero denominator.')
            grid.append([r['metric'],str(top),str(btm),str(top/btm),r['unit'],source_id(r['anchors'][0])])
    elif mode=='procedure-order':
        heads=['step','action','depends on','source'];deps={r['id']:set(r.get('after',[])) for r in rows};order=[]
        while deps:
            ready=sorted(k for k,v in deps.items() if not v)
            if not ready:raise ValueError('Missing dependency or cycle in experiment steps.')
            order+=ready
            for k in ready:del deps[k]
            for v in deps.values():v.difference_update(ready)
        reg={r['id']:r for r in rows}
        for k in order:
            r=reg[k];grid.append([k,r['text'],', '.join(r.get('after',[])),source_id(r['anchors'][0])])
        paras=[(reg[k].get('section','Methods'),reg[k]['text'],reg[k]['anchors']) for k in order]
    else:raise ValueError(mode)
    table(out/'experiment-records.tsv',heads,grid)
    sections=defaultdict(list)
    for sec,p,aa in paras:
        if p not in [entry[0] for entry in sections[sec]]:sections[sec].append((p,list(aa)))
        else:
            old=next(v for v in sections[sec] if v[0]==p)
            old[1].extend(a for a in aa if a not in old[1])
    text=['# '+plan.get('manuscript_title',title)]
    body=''
    for sec,items in sections.items():
        text.append('## '+sec);body+='<h2>'+h(sec)+'</h2>'
        for p,aa in items:
            text.append(p+' ['+'; '.join(source_id(a) for a in aa)+']')
            body+='<p>'+h(p)+' '+' '.join(link(a) for a in aa)+'</p>'
    (out/'methods.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    html_page(out/'methods.html',title,body+html_table(heads,[[h(x) for x in r] for r in grid]),anchors)
    return ['methods.md','experiment-records.tsv','methods.html',*extra]
