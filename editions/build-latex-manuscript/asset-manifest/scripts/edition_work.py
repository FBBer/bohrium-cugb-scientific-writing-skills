"""Produce typesettable manuscript components and file/line indexes with literal-safe TeX escaping."""
import csv,re
from collections import defaultdict
from pathlib import Path
from sourcebook import dump,h,html_page,html_table,source_id,table
LITERAL={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
def esc(s):return ''.join(LITERAL.get(c,c) for c in str(s))
def bare(line):return re.split(r'(?<!\\)%',line,maxsplit=1)[0]
def produce(mode,sources,rows,plan,out,title):
    if mode=='typeset-tables':
        chosen=plan['table'];path=(sources.root/chosen).resolve()
        if not path.is_relative_to(sources.root) or not path.is_file():raise ValueError('Table must be inside the materials.')
        with path.open(encoding='utf-8-sig',newline='') as f:data=list(csv.reader(f,delimiter='\t' if path.suffix.lower()=='.tsv' else ','))
        if not data or not data[0] or any(len(r)!=len(data[0]) for r in data):raise ValueError('Use a rectangular CSV or TSV table.')
        cols=len(data[0]); alignment=''.join('r' if len(data)>1 and all(re.fullmatch(r'[-+−]?\d+(?:\.\d+)?',r[i].strip()) for r in data[1:] if r[i]) and any(r[i] for r in data[1:]) else 'l' for i in range(cols))
        tex=[r'\begin{longtable}{'+alignment+'}',r'\caption{'+esc(plan.get('caption',path.stem))+r'}\\',r'\toprule',' & '.join(map(esc,data[0]))+r' \\',r'\midrule\endfirsthead',r'\toprule',' & '.join(map(esc,data[0]))+r' \\',r'\midrule\endhead',*(' & '.join(map(esc,r))+r' \\' for r in data[1:]),r'\bottomrule',r'\end{longtable}']
        (out/'table.tex').write_text('\n'.join(tex)+'\n',encoding='utf-8')
        (out/'preview.tex').write_text(r'\documentclass{article}\usepackage{longtable,booktabs}\begin{document}\input{table}\end{document}'+'\n',encoding='utf-8')
        html_page(out/'table.html',plan.get('caption',title),html_table(data[0],[[h(v) for v in r] for r in data[1:]]));return ['table.tex','preview.tex','table.html']
    scanned=[r for r in sources.rows if r['source'].lower().endswith('.tex')]
    if not scanned:raise ValueError('No TeX manuscript found.')
    vals=[]
    if mode=='reference-atlas':
        labels=defaultdict(list);refs=[]
        for r in scanned:
            s=bare(r['text'])
            for key in re.findall(r'\\label\s*\{([^{}]+)\}',s):labels[key].append(source_id(r))
            for keylist in re.findall(r'\\(?:eqref|ref|pageref|autoref|cref|Cref)\*?\s*\{([^{}]+)\}',s):
                for k in keylist.split(','):refs.append((k.strip(),source_id(r)))
        for k,where in refs:
            found=labels.get(k,[]);vals.append([k,where,' / '.join(found),'unique' if len(found)==1 else 'ambiguous' if found else 'missing'])
        for k,places in labels.items():
            if not any(a==k for a,b in refs):vals.append([k,'',' / '.join(places),'unreferenced'])
        heads=['key','use','definition','state']
    elif mode=='asset-manifest':
        heads=['manuscript','directive','requested','resolved']; files={p.relative_to(sources.root).as_posix() for p in sources.root.rglob('*') if p.is_file() and not p.is_symlink()}
        for r in scanned:
            for typ,t in re.findall(r'\\(includegraphics|input|include|bibliography|addbibresource)\s*(?:\[[^\]]*\])?\s*\{([^{}]+)\}',bare(r['text'])):
                for one in t.split(','):
                    local=Path(r['source']).parent/one.strip(); ext=[''] if local.suffix else (['.pdf','.png','.jpg','.jpeg','.eps'] if typ=='includegraphics' else ['.bib'] if 'bib' in typ else ['.tex'])
                    choices=[s for base in (local,Path(one.strip())) for e in ext if (s:=base.as_posix()+e) in files];vals.append([source_id(r),typ,one,', '.join(dict.fromkeys(choices))])
    elif mode=='notation-register':
        heads=['control sequence','definition / occurrence','location','text']
        for r in scanned:
            s=bare(r['text']);decl=set(re.findall(r'\\(?:newcommand|renewcommand|providecommand)\*?\s*\{?\\([A-Za-z@]+)',s))
            for cmd in sorted(set(re.findall(r'\\([A-Za-z@]+)',s)) & set(plan['symbols'])):vals.append([cmd,'definition' if cmd in decl else 'use',source_id(r),s])
    elif mode=='float-catalog':
        heads=['file','environment','start','caption','label'];cur=None
        for r in scanned:
            s=bare(r['text']);begin=re.search(r'\\begin\{(figure\*?|table\*?)\}',s)
            if begin:cur=[r['source'],begin[1],r['loc'],'','']
            if cur and cur[0]==r['source']:
                cap=re.search(r'\\caption(?:\[[^\]]*\])?\s*\{([^{}]*)\}',s);label=re.search(r'\\label\{([^{}]+)\}',s)
                if cap:cur[3]=cap[1]
                if label:cur[4]=label[1]
                if r'\end{'+cur[1]+'}' in s:vals.append(cur);cur=None
        if cur:vals.append(cur)
    else:raise ValueError(mode)
    table(out/'manuscript-register.tsv',heads,vals);dump(out/'manuscript-register.json',[dict(zip(heads,r)) for r in vals])
    html_page(out/'manuscript-register.html',title,html_table(heads,[[h(x) for x in r] for r in vals]));return ['manuscript-register.tsv','manuscript-register.json','manuscript-register.html']
