"""Extract page-level structure with physical page and bounding-box evidence."""
import re
from collections import Counter,defaultdict
from statistics import median
from urllib.parse import quote
from sourcebook import dump,h,html_page,html_table,table
LABEL = re.compile(r'(?i)(?<![A-Za-z])(Table|Figure|Fig\.|Tab\.|图|表)\s*([A-Z]?\d+(?:[.\-]\d+)*[a-z]?)')
def key(match):
    typ,num=match.groups()
    return ('table' if typ.lower() in {'table','tab.','表'} else 'figure')+' '+num.lower()

def produce(mode,sources,rows,plan,out,title):
    try:import pymupdf as fitz
    except ImportError:import fitz
    records=[]; readable_pages=0
    for p in sorted(sources.root.rglob('*')):
        if p.is_symlink() or p.suffix.lower()!='.pdf' or not p.is_file():continue
        name=p.relative_to(sources.root).as_posix()
        try:doc=fitz.open(p)
        except (RuntimeError,ValueError):continue
        with doc:
            if doc.needs_pass:continue
            readable_pages += len(doc)
            pages=[];sizes={};image_counts={}
            for no,page in enumerate(doc,1):
                sizes[no]=(page.rect.width,page.rect.height);image_counts[no]=len(page.get_images())
                page_lines=[]
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines',[]):
                        spans=line['spans']; txt=''.join(s['text'] for s in spans).strip()
                        if txt:page_lines.append({'page':no,'text':txt,'bbox':[round(v,2) for v in line['bbox']],'size':round(max(s['size'] for s in spans),2)})
                pages.append(page_lines)
            def add(kind,row,detail):
                records.append({'file':name,'kind':kind,**row,'detail':detail})
            if mode=='caption-links':
                caps=defaultdict(list); mentions=[]
                for pg in pages:
                    for r in pg:
                        for m in LABEL.finditer(r['text']):
                            after=r['text'][m.end():].strip()
                            if m.start()==0 and (not after or re.match(r'^[:：.、—\-]',after)):
                                caps[key(m)].append(r)
                            else:mentions.append((key(m),r))
                for k,r in mentions:
                    hits=caps.get(k,[]);add('callout',r,{'label':k,'state':'linked' if len(hits)==1 else 'ambiguous' if hits else 'unresolved','targets':[{'page':v['page'],'bbox':v['bbox'],'caption':v['text']} for v in hits]})
                for k,rs in caps.items():
                    for r in rs:add('caption',r,{'label':k})
            elif mode=='printed-folios':
                for pgno,pg in enumerate(pages,1):
                    height=sizes[pgno][1]
                    hits=[r for r in pg if (r['bbox'][3]<=height*.14 or r['bbox'][1]>=height*.86) and re.fullmatch(r'(?i)\s*(?:page\s+|第\s*)?(?:[ivxlcdm]+|\d+)(?:\s*页)?\s*',r['text'])]
                    add('page',hits[0] if len(hits)==1 else {'page':pgno,'text':'','bbox':[]},{'printed':hits[0]['text'] if len(hits)==1 else None,'candidates':[r['text'] for r in hits],'pdf_label':doc[pgno-1].get_label() or None})
            elif mode=='marginalia':
                places=defaultdict(set)
                def signature(r):
                    height=sizes[r['page']][1]
                    region='header' if r['bbox'][3]<=.12*height else 'footer' if r['bbox'][1]>=.88*height else ''
                    return region,re.sub(r'\d+', '#',r['text']).casefold()
                for pg in pages:
                    for r in pg:
                        region,s=signature(r)
                        if region:places[region,s].add(r['page'])
                for pg in pages:
                    for r in pg:
                        location=signature(r)
                        if location[0] and len(places[location])>=max(2,(len(pages)+1)//2):
                            add(location[0],r,{'pages':sorted(places[location]),'normalized':location[1]})
            elif mode=='note-pairs':
                for no,pg in enumerate(pages,1):
                    height=sizes[no][1]
                    normal=median([r['size'] for r in pg]) if pg else 0
                    for note in pg:
                        m=re.match(r'^([0-9]{1,2}|[*†‡])(?:[.)]|\s)\s*(.+)',note['text'])
                        if not m or note['bbox'][1]<.65*height or note['size']>normal:continue
                        mark=m[1]
                        source=[{'text':r['text'],'bbox':r['bbox']} for r in pg if r['bbox'][3]<note['bbox'][1] and re.search(r'(?:\['+re.escape(mark)+r'\]|(?<=\w)'+re.escape(mark)+r'(?!\w))',r['text'])]
                        add('footnote',note,{'marker':mark,'callouts':source,'state':'linked' if len(source)==1 else 'ambiguous' if source else 'unresolved'})
            elif mode=='page-coverage':
                for no,pg in enumerate(pages,1):
                    chars=sum(len(r['text']) for r in pg); bad=sum(r['text'].count('\ufffd') for r in pg)
                    add('page',{'page':no,'text':pg[0]['text'] if pg else '', 'bbox':pg[0]['bbox'] if pg else []},{'characters':chars,'images':image_counts[no],'replacement_glyphs':bad,'status':'text' if chars>=40 and not bad else 'inspect text' if chars else 'image without text' if image_counts[no] else 'blank or vector-only'})
            elif mode=='outline-map':
                toc=doc.get_toc(); bypage=defaultdict(list)
                for depth,label,no in toc:bypage[no].append((depth,label))
                ordered=[r['size'] for pg in pages for r in pg]
                normal=median(ordered) if ordered else 0
                for no,pg in enumerate(pages,1):
                    if bypage[no]:
                        for depth,label in bypage[no]:
                            seen=next((r for r in pg if label.casefold() in r['text'].casefold()),None)
                            add('bookmark',seen or {'page':no,'text':label,'bbox':[]},{'level':depth,'origin':'embedded outline'})
                    else:
                        for r in pg:
                            if len(r['text'])<=110 and r['size']>=normal*1.18:
                                add('candidate heading',r,{'origin':'type size','body_size':normal})
            else:raise ValueError(mode)
    if not readable_pages:raise ValueError('A readable PDF is required.')
    dump(out/'page-evidence.json',records)
    table(out/'page-evidence.tsv',['file','physical_page','kind','excerpt','bbox','detail'],[[r['file'],r['page'],r['kind'],r['text'],str(r['bbox']),str(r['detail'])] for r in records])
    matrix=html_table(['文件与物理页','类型','原文','定位结果'],[[h(r['file'])+' · '+h(r['page']),h(r['kind']),h(r['text']),h('; '.join(str(k)+' = '+str(v) for k,v in r['detail'].items() if v not in (None,[],'')))] for r in records])
    illustrations=[]
    if mode in {'caption-links','note-pairs','marginalia','page-coverage'}:
        from collections import OrderedDict
        selected=OrderedDict()
        for r in records:
            keypair=(r['file'],r['page'])
            if keypair not in selected and len(selected)<16:selected[keypair]=[]
            if keypair in selected:selected[keypair].append(r)
        for i,((filename,number),marks) in enumerate(selected.items(),1):
            with fitz.open(sources.root/filename) as doc:
                pg=doc[number-1]; rect=pg.rect
                if mode=='marginalia' and marks:
                    mark=next((v for v in marks if v['kind']=='header'),marks[0]); bound=fitz.Rect(mark['bbox']);clip=fitz.Rect(0,max(0,bound.y0-20),rect.width,min(rect.height,bound.y1+20))
                elif mode=='note-pairs' and marks:
                    bound=fitz.Rect(marks[0]['bbox']);clip=fitz.Rect(0,max(0,bound.y0-26),rect.width,min(rect.height,bound.y1+26))
                else:clip=rect
                for mark in marks[:35]:
                    if mark['bbox']:
                        pg.draw_rect(fitz.Rect(mark['bbox']),color=(0,0,0),width=.8)
                image='page-'+str(i)+'.png';pg.get_pixmap(matrix=fitz.Matrix(1.1,1.1),clip=clip,alpha=False).save(out/image)
                illustrations.append((image,filename,number))
    plate='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem">'+''.join('<figure style="margin:0"><img style="max-width:100%;border:1px solid black" alt="'+h(n)+' p.'+str(k)+'" src="'+h(f)+'"><figcaption>'+h(n)+' · '+str(k)+'</figcaption></figure>' for f,n,k in illustrations)+'</div>' if illustrations else ''
    if mode=='printed-folios':
        plate='<dl>'+''.join('<dt>'+h(r['file'])+' · PDF '+str(r['page'])+'</dt><dd>'+h(r['detail']['printed'] or '—')+'</dd>' for r in records)+'</dl>'
    if mode=='outline-map':
        plate='<nav><ol>'+''.join('<li>'+h(r['text'])+' · p.'+str(r['page'])+'</li>' for r in records)+'</ol></nav>'
    html_page(out/'pages.html',title,(plate+matrix) if records else '<p>材料中未定位到相应的版面元素。</p>',layout='ledger')
    return ['page-evidence.json','page-evidence.tsv','pages.html',*[i[0] for i in illustrations]]
