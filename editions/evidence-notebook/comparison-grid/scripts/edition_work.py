"""Research notebook editions: exact passage retrieval, evidence synthesis and teaching outputs."""
import json
import re
import sqlite3
from collections import defaultdict
from decimal import Decimal
from sourcebook import dump,h,html_page,html_table,link,source_id,table

def produce(mode, sources, rows, plan, out, title):
    anchors=[a for r in rows for a in r['anchors']]
    if mode=='passage-finder':
        filename='passages.sqlite'
        target=out/filename
        with sqlite3.connect(target) as db:
            db.execute('DROP TABLE IF EXISTS passage');db.execute('DROP TABLE IF EXISTS search')
            db.execute('CREATE TABLE passage(id INTEGER PRIMARY KEY,source TEXT,loc TEXT,section TEXT,line TEXT)')
            db.execute('CREATE VIRTUAL TABLE search USING fts5(line,section,source,tokenize="unicode61")')
            current={}
            for i,r in enumerate(sources.rows,1):
                match=re.match(r'^#{1,6}\s+(.+)|^\d+(?:\.\d+)*\.?\s+([A-Z\u4e00-\u9fff].{0,55})$',r['text'])
                if match: current[r['source']]=next(v for v in match.groups() if v)
                sec=current.get(r['source'],'')
                db.execute('INSERT INTO passage VALUES(?,?,?,?,?)',(i,r['source'],r['loc'],sec,r['text']))
                db.execute('INSERT INTO search(rowid,line,section,source) VALUES(?,?,?,?)',(i,r['text'],sec,r['source']))
        groups=defaultdict(list)
        for r in sources.rows: groups[r['source']].append(r)
        body='<label>查找原文 <input id="query" type="search"></label>'+''.join('<section><h2>'+h(n)+'</h2>'+''.join('<p class="hit"><b>'+h(r['loc'])+'</b> '+h(r['text'])+'</p>' for r in g)+'</section>' for n,g in groups.items())
        body+='<script>document.getElementById("query").addEventListener("input",function(){const q=this.value.trim().toLocaleLowerCase();for(const el of document.querySelectorAll(".hit"))el.hidden=!el.textContent.toLocaleLowerCase().includes(q)})</script>'
        html_page(out/'reader.html',title,body)
        return [filename,'reader.html']
    if mode=='comparison-grid':
        studies=list(dict.fromkeys(r['study'] for r in rows)); criteria=list(dict.fromkeys(r['dimension'] for r in rows))
        cells=defaultdict(list)
        for r in rows: cells[r['dimension'],r['study']].append(r)
        grids=[[d]+[' / '.join(r['text'] for r in cells[d,s]) for s in studies] for d in criteria]
        table(out/'comparison.tsv',['Dimension',*studies],grids)
        body=html_table(['比较维度',*studies],[[h(d)]+['<br>'.join(h(r['text'])+' '+link(r['anchors'][0]) for r in cells[d,s]) or '—' for s in studies] for d in criteria])
        html_page(out/'comparison.html',title,body,anchors,'ledger')
        return ['comparison.tsv','comparison.html']
    if mode=='recall-deck':
        table(out/'recall.tsv',['Question','Answer','Source','Excerpt'],[[r['question'],r['text'],source_id(r['anchors'][0]),r['anchors'][0]['quote']] for r in rows])
        html_page(out/'recall.html',title,''.join('<details><summary>'+h(r['question'])+'</summary><p>'+h(r['text'])+'</p>'+link(r['anchors'][0])+'</details>' for r in rows),anchors)
        return ['recall.tsv','recall.html']
    if mode=='numerical-notes':
        numbers=[]
        for r in rows:
            if len(r['anchors'])!=2:raise ValueError('Supply one source for each operand.')
            aa=[Decimal(str(v)) for v in r['values']]
            if len(aa)!=2:raise ValueError('Two operands required.')
            for v,a in zip(aa,r['anchors']):
                if not any(Decimal(x)==v for x in re.findall(r'(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])',a['quote'])):raise ValueError('operand absent from source')
            if len(r['units'])!=2 or r['units'][0]!=r['units'][1]:raise ValueError('Normalize operand units explicitly before comparing.')
            op=r['operation']
            if op=='difference':v,u=aa[1]-aa[0],r['units'][0]
            elif op=='ratio' and aa[0]!=0:v,u=aa[1]/aa[0],'1'
            else:raise ValueError('Undefined operation or zero denominator')
            numbers.append({'label':r['text'],'result':str(v),'unit':u,'operands':list(map(str,aa)),'operation':op,'anchors':r['anchors']})
        dump(out/'derivations.json',numbers)
        body=html_table(['派生量','计算','结果','原始读数'],[[h(n['label']),h((' → ').join(n['operands'])),h(n['result']+' '+n['unit']),' · '.join(link(x) for x in n['anchors'])] for n in numbers])
        html_page(out/'calculations.html',title,body,anchors)
        return ['derivations.json','calculations.html']
    if mode=='limitations-map':
        for r in rows:
            if len(r['anchors'])<2:raise ValueError('Pair each finding with an explicit scope or limitation passage.')
        dump(out/'scope.json',[{'finding':r['text'],'limit':r['limit'],'finding_source':r['anchors'][0],'limit_source':r['anchors'][1]} for r in rows])
        body=''.join('<section><h2>'+h(r['text'])+'</h2><div class="pair"><p>'+h(r['anchors'][0]['quote'])+' '+link(r['anchors'][0])+'</p><p>'+h(r['limit'])+' '+link(r['anchors'][1])+'</p></div></section>' for r in rows)
        html_page(out/'scope.html',title,body,anchors,'cards')
        return ['scope.json','scope.html']
    if mode=='protocol-outline':
        ordered=sorted(rows,key=lambda r: int(r['step']))
        if len(set(int(r['step']) for r in rows))!=len(rows): raise ValueError('Duplicate protocol step')
        table(out/'protocol.tsv',['step','action','material','condition','source'],[[r['step'],r['text'],r['material'],r['condition'],source_id(r['anchors'][0])] for r in ordered])
        html_page(out/'protocol.html',title,'<ol>'+''.join('<li><h2>'+h(r['text'])+'</h2><p>'+h(r['material'])+' · '+h(r['condition'])+' '+link(r['anchors'][0])+'</p></li>' for r in ordered)+'</ol>',anchors,'timeline')
        return ['protocol.tsv','protocol.html']
    raise ValueError(mode)
