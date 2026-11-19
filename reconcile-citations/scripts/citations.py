"""Deduplicate supported bibliographic records and renumber numerical citations in reading order."""
import argparse
import collections
import json
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
from casework import read,write,atomic_text


def norm(s):
    return " ".join(re.findall(r"\w+",unicodedata.normalize("NFKC",s or "").casefold()))
def doi(s):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)","",str(s or "").strip(),flags=re.I).casefold().rstrip(".,;")
def year(r):
    date=r.get("issued",{}).get("date-parts",[])
    return (date[0][0] if date and date[0] else r.get("year"))
def author_sig(r):
    return tuple((norm(a.get("family",a.get("literal",""))),norm(a.get("given",""))) for a in r.get("author",[]) if isinstance(a,dict))
def import_records(path):
    if path.suffix.lower()==".json":
        data=read(path);return data if isinstance(data,list) else data["references"]
    if path.suffix.lower() in {".ris",".enw"}:
        result=[];fields=collections.defaultdict(list);last=None
        def finish():
            if not fields:return
            pick=lambda *kk:next((fields[k][0] for k in kk if fields.get(k)),"")
            item={"id":pick("ID","F") or str(len(result)+1),"title":pick("TI","T1","T"),"DOI":pick("DOI","DO","R"),"container-title":pick("JO","JF","T2","J"),"volume":pick("VL","V"),"issue":pick("IS","N"),"page":"–".join(x for x in [pick("SP","P"),pick("EP")] if x),"type":{"JOUR":"article-journal","journal article":"article-journal","CONF":"paper-conference"}.get(pick("TY","0"),"document")}
            y=re.search(r"\d{4}",pick("PY","Y1","D"))
            if y:item["issued"]={"date-parts":[[int(y.group())]]}
            item["author"]=[]
            for name in fields.get("AU",fields.get("A1",fields.get("A",[]))):
                parts=[s.strip() for s in name.split(",",1)]
                item["author"].append({"family":parts[0],"given":parts[1]} if len(parts)==2 else {"literal":name})
            result.append({k:v for k,v in item.items() if v})
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m=re.match(r"^([A-Z0-9]{2})  -\s?(.*)$|^%([A-Z0-9])\s+(.*)$",line)
            if not m:
                if last and line.strip(): fields[last][-1]+=" "+line.strip()
                continue
            tag=m[1] or m[3];val=m[2] if m[1] else m[4]
            if tag in {"TY","0"} and fields:finish();fields.clear()
            if tag=="ER":finish();fields.clear();last=None
            else:fields[tag].append(val);last=tag
        finish();return result
    if not shutil.which("pandoc"): raise ValueError("BibTeX needs Pandoc; normalize actual records manually to CSL JSON and retain original.")
    reader="biblatex" if path.suffix.lower()==".bib" else None
    if not reader:raise ValueError("unsupported input; supply CSL JSON, BibTeX, RIS or tagged EndNote")
    r=subprocess.run(["pandoc","-f",reader,"-t","csljson",str(path)],capture_output=True,check=True,timeout=45)
    return json.loads(r.stdout)


def groups(records):
    merged=[];mapping={};bydoi={};byfinger={};decisions=[];issues=[]
    for i,orig in enumerate(records,1):
        r=dict(orig); rid=str(r.get("id",i))
        if rid in mapping:raise ValueError("duplicate input identifier "+rid+"; disambiguate first")
        ids=doi(r.get("DOI",r.get("doi"))); d=ids if re.fullmatch(r"10\.\d{4,9}/\S+",ids) else ""
        if ids and not d:issues.append({"id":rid,"issue":"invalid DOI syntax","value":ids})
        f=(norm(r.get("title")),str(year(r) or ""),author_sig(r),r.get("type",""))
        candidates=bydoi.get(d,[]) if d else []
        compatible=[j for j in candidates if not f[0] or not norm(merged[j].get("title")) or norm(merged[j].get("title"))==f[0]]
        idx=compatible[0] if len(compatible)==1 else None;reason="same normalized DOI"
        if candidates and idx is None:
            issues.append({"id":rid,"issue":"same DOI, conflicting identity; retained separate pending source verification","variants":[merged[j].get("title") for j in candidates]+[r.get("title")]})
        if idx is None and f[0] and f[1] and f[2] and f[3] and f in byfinger:
            previous=byfinger[f];prev=doi(merged[previous].get("DOI"))
            if d and prev and d!=prev:issues.append({"id":rid,"issue":"similar metadata with distinct DOIs; retain versions"})
            else:idx=previous;reason="exact normalized title, author list, year and type"
        if idx is None:idx=len(merged);merged.append(r)
        else:
            base=merged[idx]
            if reason=="same normalized DOI" and f[0] and norm(base.get("title")) and f[0]!=norm(base.get("title")):
                issues.append({"id":rid,"issue":"same DOI, conflicting title; check primary source","variants":[base.get("title"),r.get("title")]})
            for k,v in r.items():
                if not base.get(k) and v:base[k]=v
            decisions.append({"from":rid,"to":str(merged[idx].get("id",idx+1)),"reason":reason})
        if d:
            if idx not in bydoi.setdefault(d,[]):bydoi[d].append(idx)
            merged[idx]["DOI"]=d
        byfinger[f]=idx;mapping[rid]=idx
    return merged,mapping,decisions,issues


CITE=re.compile(r"\[(\d+(?:\s*[-–—,，;；]\s*\d+)*)\]")
PROTECTED=re.compile(r"\x60\x60\x60[\s\S]*?\x60\x60\x60|\x60[^\x60\n]*\x60|\$\$[\s\S]*?\$\$|\$[^$\n]+\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\[[^\]\n]*\]\([^\n)]*\)")
def expand(s):
    nums=[]
    for part in re.split(r"\s*[,，;；]\s*",s):
        bounds=re.split(r"\s*[-–—]\s*",part);a=int(bounds[0]);b=int(bounds[-1])
        if b<a or b-a>500: raise ValueError("invalid citation range "+part)
        nums.extend(str(i) for i in range(a,b+1))
    return nums
def compact(values):
    runs=[]
    for n in sorted(set(values)):
        if runs and runs[-1][-1]+1==n:runs[-1].append(n)
        else:runs.append([n])
    return ",".join(str(x[0])+"–"+str(x[-1]) if len(x)>=3 else ",".join(map(str,x)) for x in runs)


REF_HEAD=re.compile(r"(?im)^(?:#{1,6}\s+)?(?:references|bibliography|参考文献)[ \t]*[:：]?[ \t]*$|^\\(?:section|chapter)\*?\{(?:References|Bibliography|参考文献)\}[ \t]*$")
NEXT_SECTION=re.compile(r"(?im)^(?:#{1,6}\s+\S|\\(?:section|chapter)\*?\{|(?:appendix|supplementary materials|附录)(?:\s|$))")
REF_ENTRY=re.compile(r"(?m)^[ \t]*(?:\[(\d+)\]|(\d+)[.)、])[ \t]*(.*(?:\n(?![ \t]*(?:\[\d+\]|\d+[.)、]))[^\n]+)*)")

def reconcile(records,manuscript,labels=None):
    merged,mapping,decisions,issues=groups(records)
    if labels is None:
        labels={str(i):str(r.get("id",i)) for i,r in enumerate(records,1)}
    ordering={};occ=[];protected=[m.span() for m in PROTECTED.finditer(manuscript)]
    def replace(m):
        if any(a<=m.start()<b for a,b in protected):return m[0]
        try:old=expand(m[1])
        except ValueError as exc:issues.append({"offset":m.start(),"issue":str(exc)});return m[0]
        unknown=[k for k in old if str(labels.get(k,"")) not in mapping]
        if unknown:
            issues.append({"offset":m.start(),"issue":"unresolved citation label","labels":unknown});return m[0]
        idxs=[mapping[str(labels[k])] for k in old]
        for idx in idxs:ordering.setdefault(idx,len(ordering)+1)
        new="["+compact([ordering[i] for i in idxs])+"]"
        occ.append({"source_offsets":[m.start(),m.end()],"old":m[0],"new":new,"record_ids":[str(merged[i].get("id",i+1)) for i in idxs]});return new
    heading=REF_HEAD.search(manuscript)
    if heading:
        tail=manuscript[heading.end():];following=NEXT_SECTION.search(tail)
        end=heading.end()+(following.start() if following else len(tail))
        ref_block=manuscript[heading.end():end]
        entries={str(m[1] or m[2]):m[3].strip() for m in REF_ENTRY.finditer(ref_block)}
        body=CITE.sub(replace,manuscript[:heading.start()])
        def suffix_replace(match):
            # Offsets in the audit are against the full source, including the bibliography.
            return replace(match)
        suffix_parts=[];last=end
        for match in CITE.finditer(manuscript,end):
            suffix_parts += [manuscript[last:match.start()],suffix_replace(match)];last=match.end()
        suffix="".join(suffix_parts)+manuscript[last:]
        new_entries=[]
        for idx,n in ordering.items():
            old=next((label for label,rid in labels.items() if mapping.get(str(rid))==idx and str(label) in entries),None)
            if old is None:
                issues.append({"issue":"bibliography block requires formatting for an unmapped record","record":merged[idx].get("id")})
            else:new_entries.append("["+str(n)+"] "+entries[str(old)])
        complete=bool(entries) and len(new_entries)==len(ordering)
        if not complete:issues.append({"issue":"original bibliography retained, review original entry labels and format"})
        revised=body+heading[0]+("\n\n"+"\n".join(new_entries)+"\n\n" if complete else ref_block)+suffix
    else:
        revised=CITE.sub(replace,manuscript)
    used=[{"number":num,"record":merged[idx]} for idx,num in ordering.items()]
    return revised,{"cited":used,"uncited":[r for i,r in enumerate(merged) if i not in ordering],"merge_decisions":decisions,"occurrences":occ,"issues":issues}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("records",type=Path);p.add_argument("manuscript",type=Path);p.add_argument("out",type=Path);p.add_argument("--labels")
    a=p.parse_args();text,report=reconcile(import_records(a.records),a.manuscript.read_text(encoding="utf-8"),read(a.labels) if a.labels else None)
    atomic_text(a.out/"manuscript.md",text);write(a.out/"citation-audit.json",report);write(a.out/"cited.csl.json",[r["record"] for r in report["cited"]])
