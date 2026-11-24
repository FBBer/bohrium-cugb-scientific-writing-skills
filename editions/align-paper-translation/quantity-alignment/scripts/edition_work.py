"""Bilingual revision artifacts with intact segment identifiers and source passages."""
import re
from collections import defaultdict
from xml.etree import ElementTree as ET
from sourcebook import dump,h,html_page,html_table,link,source_id,table

DIGIT=re.compile(r'[<>≤≥±−+\-]?\d+(?:[.,]\d+)?(?:[eE][+\-]?\d+)?')
TERM=re.compile(r'(?i)(?<!\w)(?:not|no|never|may|might|possibly|only|at least|at most|up to|approximately|below|above)(?!\w)|不能|并未|不显著|没有|可能|仅|至少|至多|大约|低于|高于')
def produce(mode,sources,rows,plan,out,title):
    src=plan.get('source_lang','en'); dst=plan.get('target_lang','zh'); anchors=[r['anchors'][0] for r in rows]
    for r in rows:
        if not str(r.get('target','')).strip():raise ValueError('Every translated segment requires target text.')
    if mode in {'translation-memory','review-exchange'}:
        if mode=='translation-memory':
            root=ET.Element('tmx',version='1.4');ET.SubElement(root,'header',{'creationtool':'research-editions','creationtoolversion':'1','segtype':'sentence','o-tmf':'UTF-8','adminlang':'en','srclang':src,'datatype':'plaintext'})
            body=ET.SubElement(root,'body')
            for r in rows:
                unit=ET.SubElement(body,'tu',tuid=r['id']);ET.SubElement(unit,'prop',type='source-location').text=source_id(r['anchors'][0])
                for lang,txt in [(src,r['anchors'][0]['quote']),(dst,r['target'])]:
                    uv=ET.SubElement(unit,'tuv',{'{http://www.w3.org/XML/1998/namespace}lang':lang});ET.SubElement(uv,'seg').text=txt
            name='segments.tmx'
        else:
            ns='urn:oasis:names:tc:xliff:document:2.0';root=ET.Element('xliff',xmlns=ns,version='2.0',srcLang=src,trgLang=dst)
            files={}
            for r in rows:
                a=r['anchors'][0]; f=a['source']
                if f not in files:files[f]=ET.SubElement(root,'file',id='f'+str(len(files)+1),original=f)
                u=ET.SubElement(files[f],'unit',id=r['id']); notes=ET.SubElement(u,'notes');ET.SubElement(notes,'note').text=source_id(a)
                seg=ET.SubElement(u,'segment',state='translated');ET.SubElement(seg,'source').text=a['quote'];ET.SubElement(seg,'target').text=r['target']
            name='bilingual.xlf'
        ET.ElementTree(root).write(out/name,encoding='utf-8',xml_declaration=True)
        body=''.join('<section><h2>'+h(r['id'])+'</h2><div class="pair"><p>'+h(r['anchors'][0]['quote'])+'</p><p>'+h(r['target'])+'</p></div></section>' for r in rows)
        html_page(out/'parallel.html',title,body,anchors,'cards')
        return [name,'parallel.html']
    if mode=='term-concordance':
        terms=plan['glossary']; tally=[]
        for source_term,preferred in terms.items():
            for r in rows:
                if source_term.casefold() in r['anchors'][0]['quote'].casefold():
                    tally.append([source_term,preferred,r['id'],r['target'], 'present' if preferred.casefold() in r['target'].casefold() else 'review',source_id(r['anchors'][0])])
        table(out/'concordance.tsv',['source term','preferred translation','segment','actual translation','status','location'],tally)
        html_page(out/'glossary.html',title,html_table(['原词','约定译名','分段','译文','状态','出处'],[[h(x) for x in r] for r in tally]),anchors,'ledger')
        return ['concordance.tsv','glossary.html']
    if mode=='quantity-alignment':
        observed=[]
        for r in rows:
            a=r['anchors'][0]; sf=DIGIT.findall(a['quote']);tf=DIGIT.findall(r['target'])
            n=lambda t:[s.replace('−','-').replace(',','') for s in t]
            observed.append({'segment':r['id'],'source_values':sf,'target_values':tf,'same_sequence':n(sf)==n(tf),'source':a,'target':r['target']})
        dump(out/'quantities.json',observed)
        html_page(out/'quantity-review.html',title,html_table(['分段','原数值','译文数值','数字次序'],[[h(r['segment']),h(' · '.join(r['source_values'])),h(' · '.join(r['target_values'])),'一致' if r['same_sequence'] else '核对原文'] for r in observed]),anchors)
        return ['quantities.json','quantity-review.html']
    if mode=='scope-alignment':
        values=[]
        for r in rows:
            a=r['anchors'][0]; left=TERM.findall(a['quote']);right=TERM.findall(r['target'])
            values.append([r['id'],' | '.join(left),' | '.join(right),r.get('decision',''),a['quote'],r['target']])
        table(out/'modality.tsv',['id','source cues','target cues','translator decision','source','target'],values)
        body=''.join('<section><h2>'+h(r[0])+'</h2><div class="pair"><p>'+h(r[4])+'</p><p>'+h(r[5])+'</p></div><p>'+h(r[1])+' → '+h(r[2])+'</p><p>'+h(r[3])+'</p></section>' for r in values)
        html_page(out/'scope-review.html',title,body,anchors,'cards')
        return ['modality.tsv','scope-review.html']
    raise ValueError(mode)
