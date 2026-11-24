"""Write an editable introduction with paragraph-level support and an optional cross-study exhibit."""
from collections import defaultdict
from sourcebook import dump,h,html_page,html_table,link,source_id,table
def produce(mode,sources,rows,plan,out,title):
    anchors=[a for r in rows for a in r['anchors']]
    numbers={a['ref']:i+1 for i,a in enumerate({a['ref']:a for a in anchors}.values())}
    sections=defaultdict(list); grid=[]; exhibit=''
    for row in rows:
        text=row['text']; supporting=row['anchors']
        if mode=='matched-comparisons':
            if len({a['source'] for a in supporting})<2:raise ValueError('A comparison needs passages from two distinct papers.')
            group=row['axis'];grid.append([group,row['common'],row['difference'],*[source_id(a) for a in supporting[:2]]])
        elif mode=='contribution-chain':
            if len(supporting)<2 or supporting[0]['source']==supporting[1]['source']:raise ValueError('Use separate literature and project evidence.')
            group=row['section'];grid.append([row['gap'],row['response'],row['boundary'],source_id(supporting[0]),source_id(supporting[1])])
        elif mode=='historical-thread':
            group=row['period'];grid.append([row['year'],row['change'],row['boundary'],source_id(supporting[0])])
        elif mode=='difference-in-scope':
            group=row['scope'];grid.append([group,row['covered'],row['missing'],source_id(supporting[0])])
        elif mode=='paragraph-roles':
            group=row['section'];grid.append([row['role'],row['audience'],text,source_id(supporting[0])])
        else:raise ValueError(mode)
        sections[group].append((text,supporting))
    if mode=='matched-comparisons': heads=['比较轴','共同条件','方法差异','文献一','文献二']
    elif mode=='contribution-chain':heads=['研究空白','本研究回应','适用范围','前人工作','本研究记录']
    elif mode=='historical-thread':
        grid.sort(key=lambda r:int(r[0]));heads=['年份','变化','适用范围','出处']
    elif mode=='difference-in-scope':heads=['场景','已有覆盖','证据缺口','出处']
    else:heads=['段落作用','读者','正文','出处']
    def cite(a):return '['+str(numbers[a['ref']])+']'
    paper=['# '+plan.get('manuscript_title',title)];body=''
    for sec,paras in sections.items():
        paper+=['## '+sec];body+='<section><h2>'+h(sec)+'</h2>'
        for t,aa in paras:
            paper.append(t+' '+', '.join(cite(a) for a in aa));body+='<p>'+h(t)+' '+' '.join('<a href="#'+h(a['ref'])+'">'+cite(a)+'</a>' for a in aa)+'</p>'
        body+='</section>'
    paper+=['## Sources']+[cite(a)+' '+source_id(a)+' — '+a['quote'] for a in {x['ref']:x for x in anchors}.values()]
    (out/'introduction.md').write_text('\n\n'.join(paper)+'\n',encoding='utf-8')
    table(out/'work-to-claim.tsv',heads,grid)
    dump(out/'paragraph-sources.json',[{'id':r['id'],'paragraph':r['text'],'evidence':r['anchors']} for r in rows])
    exhibit=html_table(heads,[[h(i) for i in v] for v in grid])
    html_page(out/'manuscript.html',plan.get('manuscript_title',title),body+'<details><summary>'+h(title)+'</summary>'+exhibit+'</details>',anchors)
    return ['introduction.md','work-to-claim.tsv','paragraph-sources.json','manuscript.html']
