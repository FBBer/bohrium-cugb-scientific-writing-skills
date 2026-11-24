"""Review and apply sentence edits while keeping original evidence and scientific quantities."""
import difflib,re
from collections import defaultdict
from sourcebook import dump,h,html_page,html_table,link,source_id,table

def diff(old,new):
    a=re.findall(r'\s+|[\w.]+|[^\w\s]',old);b=re.findall(r'\s+|[\w.]+|[^\w\s]',new)
    parts=[]
    for op,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if op=='equal':parts.append(h(''.join(a[i:j])))
        else:
            if i<j:parts.append('<del>'+h(''.join(a[i:j]))+'</del>')
            if k<l:parts.append('<ins>'+h(''.join(b[k:l]))+'</ins>')
    return ''.join(parts)

def produce(mode,sources,rows,plan,out,title):
    anchors=[r['anchors'][0] for r in rows]
    if mode=='abbreviation-order':
        terms=plan['abbreviations']; found=[]
        for short,long in terms.items():
            for f in sorted({r['source'] for r in sources.rows}):
                uses=[s for s in sources.rows if s['source']==f and re.search(r'(?<!\w)'+re.escape(short)+r'(?!\w)',s['text'])]
                if not uses:continue
                explicit=[s for s in uses if long.casefold() in s['text'].casefold()]
                found.append([short,long,f,uses[0]['loc'],explicit[0]['loc'] if explicit else '',bool(explicit and explicit[0]==uses[0])])
        table(out/'abbreviations.tsv',['short','long','file','first use','definition','defined on first use'],found)
        html_page(out/'first-use.html',title,html_table(['简称','全称','文件','首次出现','定义','首次释义'],[[h(v) for v in r] for r in found]))
        return ['abbreviations.tsv','first-use.html']
    changes=[]
    for r in rows:
        a=r['anchors'][0];old=a['quote'];new=r['revision']
        nums=lambda s:re.findall(r'(?:[<>≤≥±−+\-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)',s)
        locked=[v for v in plan.get('protected',[]) if v in old and v not in new]
        changes.append({'id':r['id'],'before':old,'after':new,'source':a,'new_numbers':nums(new),'old_numbers':nums(old),'lost_literals':locked,'accept':bool(r.get('accept',True)),'reason':r.get('reason','')})
    if mode=='scientific-invariants':
        for c in changes:c['quantity_change']=c['old_numbers']!=c['new_numbers']
        dump(out/'scientific-edits.json',changes)
        body=''.join('<section><h2>'+h(c['id'])+'</h2><p>'+diff(c['before'],c['after'])+'</p><p>'+h(' / '.join(c['lost_literals']))+' '+link(c['source'])+'</p></section>' for c in changes)
        html_page(out/'edits.html',title,body,anchors,'cards')
        return ['scientific-edits.json','edits.html']
    if mode=='selective-revision':
        grouped=defaultdict(list)
        for c in changes:
            if c['accept']:grouped[c['source']['source'],c['source']['loc']].append(c)
        artifacts=[]; docs=sorted({a['source'] for a in anchors})
        for i,f in enumerate(docs,1):
            rendered=[]
            for s in sources.rows:
                if s['source']!=f:continue
                orig=s['text']; spans=[]
                for c in grouped[(f,s['loc'])]:
                    start=orig.index(c['before']);spans.append((start,start+len(c['before']),c['after']))
                spans.sort()
                if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('Accepted edits overlap; choose one.')
                for x,y,v in reversed(spans):orig=orig[:x]+v+orig[y:]
                rendered.append(orig)
            n=f'revised-{i}.md';(out/n).write_text('\n\n'.join(rendered)+'\n',encoding='utf-8');artifacts.append(n)
        dump(out/'decisions.json',changes);return [*artifacts,'decisions.json']
    if mode=='argument-redline':
        body='';revision=[]
        for r,c in zip(rows,changes):
            kind=r['purpose'];body+='<section><h2>'+h(kind)+'</h2><p>'+diff(c['before'],c['after'])+'</p><p>'+h(c['reason'])+' '+link(c['source'])+'</p></section>'
            revision.append('## '+kind+'\n\n'+c['after'])
        (out/'edited-passages.md').write_text('\n\n'.join(revision)+'\n',encoding='utf-8')
        html_page(out/'editorial-letter.html',title,body,anchors,'cards');return ['edited-passages.md','editorial-letter.html']
    if mode=='style-consistency':
        variants=plan['style'];hits=[]
        for preferred,forms in variants.items():
            for s in sources.rows:
                for form in forms:
                    if re.search(r'(?<!\w)'+re.escape(form)+r'(?!\w)',s['text'],re.I):hits.append([preferred,form,s['source'],s['loc'],s['text']])
        table(out/'style.tsv',['preferred','observed','file','location','sentence'],hits)
        html_page(out/'style.html',title,html_table(['推荐写法','原文写法','文件','位置','上下文'],[[h(x) for x in r] for r in hits]));return ['style.tsv','style.html']
    raise ValueError(mode)
