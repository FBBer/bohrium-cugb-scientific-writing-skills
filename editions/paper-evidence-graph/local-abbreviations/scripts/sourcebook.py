"""Locate exact excerpts in user materials and publish a browsable evidence index."""
import csv
import hashlib
import html
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT = {'.txt', '.md', '.tex', '.rst', '.bib', '.tsv', '.csv', '.json', '.jsonl', '.yml', '.yaml'}
XML_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def compact(s):
    return ' '.join(unicodedata.normalize('NFC', str(s)).split())

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def table(path, headers, rows, sep='\t'):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, delimiter=sep)
        writer.writerow(headers)
        writer.writerows(rows)

def lines_for(path):
    suffix = path.suffix.lower()
    if suffix in TEXT:
        return [('L' + str(i), s) for i, s in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1)]
    if suffix == '.docx':
        with zipfile.ZipFile(path) as book:
            doc = ET.fromstring(book.read('word/document.xml'))
            return [('¶' + str(i), ''.join(x.text or '' for x in p.iter(XML_NS + 't')))
                    for i, p in enumerate(doc.iter(XML_NS + 'p'), 1)]
    if suffix == '.pdf':
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
        with pymupdf.open(path) as doc:
            if doc.needs_pass:
                raise ValueError('encrypted PDF')
            return [('p%d:L%d' % (i, j), line) for i,page in enumerate(doc, 1)
                    for j,line in enumerate(page.get_text(sort=True).splitlines(), 1)]
    if suffix == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            return [(s.title + '!' + str(i), ' | '.join('' if c is None else str(c) for c in row))
                    for s in book for i,row in enumerate(s.values, 1)]
        finally:
            book.close()
    return []

class Sources:
    def __init__(self, folder):
        self.root = Path(folder).resolve()
        self.rows = []
        self.notes = []
        for p in sorted(self.root.rglob('*')):
            if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(self.root):
                continue
            if p.suffix.lower() not in TEXT | {'.pdf','.docx','.xlsx'} or p.name in {'case.json','task.md','plan.json'}:
                continue
            name = p.relative_to(self.root).as_posix()
            try:
                records = [(loc, compact(s)) for loc,s in lines_for(p) if compact(s)]
            except (OSError, ValueError, RuntimeError, ImportError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
                self.notes.append({'source':name, 'reason':str(exc)})
                continue
            if not records:
                self.notes.append({'source':name,'reason':'no readable text'})
            for loc,s in records:
                self.rows.append({'source':name,'loc':loc,'text':s})

    @lru_cache(maxsize=1024)
    def resolve(self, source, quote, loc=''):
        q = compact(quote)
        if not q:
            raise ValueError('an empty excerpt cannot establish a source')
        hits = [r for r in self.rows if r['source']==source and (not loc or loc==r['loc']) and q in r['text']]
        if len(hits)!=1 or hits[0]['text'].count(q)!=1:
            raise ValueError(f'{source} {loc} has {len(hits)} matching passages for {q!r}. Supply a unique excerpt and location.')
        r = hits[0]
        identifier = hashlib.sha256((source+'\0'+r['loc']+'\0'+q).encode()).hexdigest()[:16]
        return {'source':source,'loc':r['loc'],'quote':q,'ref':'e-'+identifier}

def source_id(row):
    return row['source']+' · '+row['loc']

def h(value):
    return html.escape(str(value), quote=True)

def link(a):
    return '<a href="#'+h(a['ref'])+'">'+h(source_id(a))+'</a>'

def html_page(path, title, body, refs=(), layout='article', lang='zh'):
    items = {r['ref']:r for r in refs}
    end = ''
    if items:
        end = '<details><summary>原文出处 / Sources</summary>' + ''.join(
               '<blockquote id="%s"><b>%s</b><p>%s</p></blockquote>' % (h(k),h(source_id(v)),h(v['quote']))
               for k,v in items.items()) + '</details>'
    css = """*{box-sizing:border-box}html{color:#000;background:#fff;font:17px/1.62 system-ui,sans-serif}body{max-width:70rem;margin:0 auto;padding:2.8rem clamp(1rem,5vw,4rem)}h1,h2,h3{font-family:Georgia,'Songti SC',serif;line-height:1.23}h1{font-size:clamp(1.8rem,4vw,3rem);margin:0 0 1em}h2{margin:1.45em 0 .4em}a{color:#000;text-underline-offset:.17em}p{max-width:78ch}table{width:100%;border-collapse:collapse;margin:1em 0}th,td{vertical-align:top;text-align:left;padding:.5em .65em;overflow-wrap:anywhere}th{background:#8eb9ce;border-top:2px solid #000;border-bottom:1px solid #000}td{border-bottom:1px solid #000}blockquote{margin:1em 0;padding:.4em 1em;background:#e4ece7}dt{font-weight:700}dd{margin:.25em 0 1em}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:1.5em 0}summary{cursor:pointer;font-weight:700}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1.5em}.cards section{border-top:2px solid #000;padding:.5em 0}.timeline ol{padding-left:2em}.timeline li{margin:.7em 0}del{background:#ebc1b9}ins{background:#a7caba}.ledger tbody tr:nth-child(even){background:#e9edf1}svg{max-width:100%;height:auto}@media(max-width:600px){.pair{display:block}body{padding:1rem}table{font-size:.94em}}@media print{body{padding:0}a{text-decoration:none}tr,blockquote{break-inside:avoid}}"""
    path.write_text('<!doctype html><html lang="'+lang+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+h(title)+'</title><style>'+css+'</style><main class="'+h(layout)+'"><h1>'+h(title)+'</h1>'+body+end+'</main></html>',encoding='utf-8')

def html_table(headers, rows):
    return '<table><thead><tr>'+''.join('<th>'+h(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(
           '<tr>'+''.join('<td>'+x+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'

def exact_rows(sources, rows):
    good,issues=[],[]
    ids=set()
    for i,row in enumerate(rows,1):
        try:
            key=str(row.get('id') or i)
            if key in ids: raise ValueError('duplicate record id')
            anchors=[sources.resolve(r['source'],r['quote'],r.get('loc','')) for r in row.get('evidence',[])]
            if not anchors: raise ValueError('at least one cited excerpt is required')
            ids.add(key);good.append({**row,'id':key,'anchors':anchors})
        except (KeyError, ValueError, TypeError) as exc:
            issues.append({'row':i,'reason':str(exc)})
    return good,issues
