"""Deduplicate supported bibliographic records and renumber numerical citations in reading order."""
import argparse
from bisect import bisect_right
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
            issues.append({"id":rid,"related_ids":[rid]+[str(merged[j].get("id",j+1)) for j in candidates],
                           "issue":"same DOI, conflicting identity; retained separate pending source verification","variants":[merged[j].get("title") for j in candidates]+[r.get("title")]})
        if idx is None and f[0] and f[1] and f[2] and f[3] and f in byfinger:
            previous=byfinger[f];prev=doi(merged[previous].get("DOI"))
            if d and prev and d!=prev:
                issues.append({"id":rid,"related_ids":[rid,str(merged[previous].get("id",previous+1))],
                               "issue":"similar metadata with distinct DOIs; retain versions"})
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

SENTENCE_END=re.compile(r"[。！？!?]+|(?<!\d)\.(?=\s|$)|(?<=\d)\.(?=\s+[A-Z]|$)|\n[ \t]*\n")
ABBREVIATION=re.compile(r"\b(?:et al|e\.g|i\.e|Fig|Eq|Dr|Prof|Mr|Mrs|Ms|vs|cf|[A-Z])\Z")
BEFORE_QUANTITY=re.compile(r"\b(?:approx|ca|figs?|eqs?|nos?|secs?|chaps?|pp?|refs?|vols?)\Z",re.I)

def sentence_breaks(text):
    breaks=[]
    for match in SENTENCE_END.finditer(text):
        prior=text[max(0,match.start()-12):match.start()]
        if match[0]==".":
            following=text[match.end():match.end()+15].lstrip()
            if ABBREVIATION.search(prior) or (BEFORE_QUANTITY.search(prior) and re.match(r"[([]?\s*[+-]?\d",following)):
                continue
        breaks.append(match.end())
    return breaks

def citation_context(text,start,ends):
    index=bisect_right(ends,start)
    left=ends[index-1] if index else 0
    right=ends[index] if index<len(ends) else len(text)
    while left<right and text[left].isspace(): left+=1
    while right>left and text[right-1].isspace(): right-=1
    return {"source_offsets":[left,right],"text":text[left:right]}

def metadata_status(record,issues):
    rid=str(record.get("id",""))
    required={"title":record.get("title"),"author":record.get("author") or record.get("editor"),"year":year(record)}
    if record.get("type") in {"article-journal","paper-conference","chapter"}:
        required["container-title"]=record.get("container-title")
    missing=[name for name,value in required.items() if not value]
    conflicts=[i["issue"] for i in issues if str(i.get("id",""))==rid or rid in i.get("related_ids",[])]
    return {"record_id":rid,"field_coverage":"partial" if missing else "core_fields_present","missing_core_fields":missing,
            "doi":doi(record.get("DOI")) or None,"metadata_issues":conflicts,"external_verification":"not_performed"}

def bibliography_labels(entries, records):
    """Recover printed labels by bibliographic identity, independently of library order."""
    by_doi = collections.defaultdict(set)
    titles = []
    for i, record in enumerate(records, 1):
        ident = str(record.get("id", i))
        identifier = doi(record.get("DOI") or record.get("doi"))
        if identifier:
            by_doi[identifier].add(ident)
        title = norm(record.get("title"))
        if title:
            titles.append((title, ident))
    result = {}
    for label, entry in entries.items():
        identifiers = {doi(m.rstrip(".,;")) for m in re.findall(r"10\.\d{4,9}/[^\s<>\"]+", entry, re.I)}
        title_line = " " + norm(entry) + " "
        title_hits = {ident for title, ident in titles if " " + title + " " in title_line}
        if identifiers:
            doi_hits = set().union(*(by_doi.get(x, set()) for x in identifiers))
            hits = doi_hits & title_hits if title_hits else doi_hits
        else:
            hits = title_hits
        if len(hits) == 1:
            result[label] = hits.pop()
    return result


KEYED = re.compile(r"\[(?=[^\]\n]*@)(?:[^\]\n])+\]|\\(?:[cC]ite(?:p|t|author|year)?|parencite|textcite|autocite)\*?(?:\[[^\]\n]*\]){0,2}\{[^{}\n]+\}")
PANDOC_KEY = re.compile(r"(?<![\w.])(-?@)([\w](?:[\w:./+%-]*[\w])?)")


def keyed_groups(manuscript):
    ignored = [m.span() for m in PROTECTED.finditer(manuscript)]
    for match in KEYED.finditer(manuscript):
        if any(a<=match.start()<b for a,b in ignored):
            continue
        group = match[0]
        if group.startswith("["):
            keys = [(m[2],match.start()+m.start(2),match.start()+m.end(2)) for m in PANDOC_KEY.finditer(group)]
        else:
            content = re.search(r"\{([^{}]+)\}$",group)
            offset = match.start()+content.start(1)
            keys = [(m[0],offset+m.start(),offset+m.end()) for m in re.finditer(r"[^,\s]+",content[1])]
        if keys:
            yield match,keys


def reconcile_keys(manuscript, merged, mapping, decisions, issues, keyed):
    changes,occ,order = [],[],{}
    ends = sentence_breaks(manuscript)
    for group,keys in keyed:
        unknown=[k for k,_,_ in keys if k not in mapping]
        if unknown:
            issues.append({"offset":group.start(),"issue":"unknown citation key","keys":unknown,
                           "sentence":citation_context(manuscript,group.start(),ends)})
        corrected=group[0];matched=[]
        for key,a,b in reversed(keys):
            if key in mapping:
                idx=mapping[key];canonical=str(merged[idx].get("id",idx+1))
                if canonical!=key:
                    changes.append((a,b,canonical))
                    corrected=corrected[:a-group.start()]+canonical+corrected[b-group.start():]
        for key,_,_ in keys:
            if key in mapping:
                idx=mapping[key];order.setdefault(idx,len(order)+1);matched.append(str(merged[idx].get("id",idx+1)))
        occ.append({"source_offsets":[group.start(),group.end()],"old":group[0],"new":corrected,
                    "sentence":citation_context(manuscript,group.start(),ends),"record_ids":matched,"unresolved":unknown})
    result=manuscript
    for a,b,target in sorted(changes,reverse=True):
        result=result[:a]+target+result[b:]
    return result,{"cited":[{"number":n,"record":merged[i]} for i,n in order.items()],
                   "uncited":[r for i,r in enumerate(merged) if i not in order],"merge_decisions":decisions,
                   "numbering_status":"citation_keys_preserved","label_source":"manuscript_keys",
                   "occurrences":occ,"metadata_status":[metadata_status(r,issues) for r in merged],"issues":issues}


def reconcile_numbered_and_keyed(records,manuscript,labels=None):
    keys = list(keyed_groups(manuscript))
    if not keys:
        return numeric_references(records,manuscript,labels)
    merged,mapping,decisions,issues=groups(records)
    revised,report = reconcile_keys(manuscript,merged,mapping,decisions,issues,keys)
    protected = [m.span() for m in PROTECTED.finditer(manuscript)] + [m.span() for m,_ in keys]
    if any(not any(a<=m.start()<b for a,b in protected) for m in CITE.finditer(manuscript)):
        _, numeric = numeric_references(records,manuscript,labels,protected)
        additions = [{**o,"new":o["old"]} for o in numeric["occurrences"]]
        report["occurrences"] = sorted(report["occurrences"]+additions,key=lambda o:o["source_offsets"][0])
        for problem in numeric["issues"]:
            if problem not in report["issues"]:
                report["issues"].append(problem)
        cited_ids = list(dict.fromkeys(rid for o in report["occurrences"] for rid in o["record_ids"]))
        ids = {str(record.get("id",i)):record for i,record in enumerate(merged,1)}
        report["cited"] = [{"number":i,"record":ids[rid]} for i,rid in enumerate(cited_ids,1)]
        report["uncited"] = [r for rid,r in ids.items() if rid not in cited_ids]
        report["label_source"] = "manuscript_keys_and_"+numeric["label_source"]
        report["numbering_status"] = "mixed_original_numbers_preserved"
    return revised,report


def numeric_references(records,manuscript,labels=None,skip=None):
    merged,mapping,decisions,issues=groups(records)
    basis = "explicit" if labels is not None else "library_order_assumed"
    heading=REF_HEAD.search(manuscript)
    entries={}
    repeated_labels=set()
    if heading:
        tail=manuscript[heading.end():];following=NEXT_SECTION.search(tail)
        end=heading.end()+(following.start() if following else len(tail))
        for entry in REF_ENTRY.finditer(manuscript[heading.end():end]):
            label=entry[1] or entry[2]
            if label in entries:
                repeated_labels.add(label)
            entries[label]=entry[3].strip()
    if labels is None and entries:
        canonical = {}
        for record_id, index in mapping.items():
            canonical.setdefault(index, record_id)
        identities = [dict(record, id=canonical[index]) for index, record in enumerate(merged)]
        labels = bibliography_labels(entries, identities)
        basis = "printed_bibliography"
    elif labels is None:
        labels = {str(i):str(r.get("id",i)) for i,r in enumerate(records,1)}
    ordering={};occ=[];protected=skip if skip is not None else [m.span() for m in PROTECTED.finditer(manuscript)]
    numbering_problems=[{"issue":"duplicate original bibliography label","label":label} for label in sorted(repeated_labels)]
    original_numbers=collections.defaultdict(list)
    ends=sentence_breaks(manuscript)
    def replace(m):
        if any(a<=m.start()<b for a,b in protected):return m[0]
        try:old=expand(m[1])
        except ValueError as exc:
            numbering_problems.append({"offset":m.start(),"issue":str(exc)})
            return m[0]
        for label in old:
            idx=mapping.get(str(labels.get(label,"")))
            if idx is not None and int(label) not in original_numbers[idx]:
                original_numbers[idx].append(int(label))
        unknown=[k for k in old if str(labels.get(k,"")) not in mapping]
        if unknown:
            numbering_problems.append({"offset":m.start(),"issue":"unresolved citation label","labels":unknown,"group":old,
                                       "sentence":citation_context(manuscript,m.start(),ends)})
            return m[0]
        idxs=[mapping[str(labels[k])] for k in old]
        for idx in idxs:ordering.setdefault(idx,len(ordering)+1)
        new="["+compact([ordering[i] for i in idxs])+"]"
        occ.append({"source_offsets":[m.start(),m.end()],"old":m[0],"new":new,
                    "sentence":citation_context(manuscript,m.start(),ends),
                    "record_ids":[str(merged[i].get("id",i+1)) for i in idxs]});return new
    if heading:
        body=CITE.sub(replace,manuscript[:heading.start()])
        suffix_parts=[];last=end
        for match in CITE.finditer(manuscript,end):
            suffix_parts += [manuscript[last:match.start()],replace(match)];last=match.end()
        suffix="".join(suffix_parts)+manuscript[last:]
        new_entries=[]
        for idx,n in ordering.items():
            old=next((label for label,rid in labels.items() if mapping.get(str(rid))==idx and str(label) in entries),None)
            if old is None:
                numbering_problems.append({"issue":"bibliography entry missing for cited record","record":merged[idx].get("id")})
            else:new_entries.append("["+str(n)+"] "+entries[str(old)])
        revised=(body+heading[0]+"\n\n"+"\n".join(new_entries)+"\n\n"+suffix if ordering else manuscript)
    else:
        revised=CITE.sub(replace,manuscript)
    unknown_labels={int(label) for issue in numbering_problems for label in issue.get("labels",[])}
    mixed_group=any(set(issue.get("group",[]))-set(issue.get("labels",[])) for issue in numbering_problems)
    preserve=bool(numbering_problems) and (heading is not None or mixed_group or bool(unknown_labels.intersection(ordering.values()))
                                            or any("labels" not in issue for issue in numbering_problems))
    if preserve:
        # Body, appendix and bibliography form one numbering system. Keep them together.
        revised=manuscript
        for item in occ:
            item["new"]=item["old"]
        used=[{"number":numbers[0],"source_numbers":numbers,"record":merged[idx]}
              for idx,numbers in original_numbers.items()]
    else:
        used=[{"number":num,"record":merged[idx]} for idx,num in ordering.items()]
    issues.extend(numbering_problems)
    numbering_status="original_preserved" if preserve or not ordering else "partial" if numbering_problems else "resolved"
    return revised,{"cited":used,"uncited":[r for i,r in enumerate(merged) if i not in original_numbers],"merge_decisions":decisions,
                    "numbering_status":numbering_status,"label_source":basis,
                    "occurrences":occ,"metadata_status":[metadata_status(r,issues) for r in merged],"issues":issues}


YEAR_TOK = r"(?:1[5-9]\d{2}|20\d{2})(?:[a-z])?"
YEAR_GROUP = re.compile(r"[（(]([^()（）\n]{1,430})[）)]")
LESS_LOCATOR = re.compile(r"(?:\s*[,，]\s*(?:pp?\.|pages?|chap\.|sec\.)\s*[\d–—-]+)\s*$",re.I)


def author_year_occurrences(manuscript, records, ignored):
    """Bind printed author/year citations to the supplied library; never invent suffixes."""
    signatures, known = {}, []
    for index,rec in enumerate(records,1):
        authors = [str(a.get("family") or a.get("literal") or "").strip() for a in rec.get("author",[]) if isinstance(a,dict)]
        authors = [name for name in authors if name]
        yr = str(year(rec) or "")
        if not authors or not re.fullmatch(YEAR_TOK,yr):
            continue
        suffix = yr[4:] or str(rec.get("year-suffix") or "")
        labels = {authors[0]} if len(authors)==1 else {authors[0]+" et al.",authors[0]+" et al",authors[0]+"等"}
        if len(authors)>1:
            for sep in (" and "," & ","和","与"):
                labels.add(", ".join(authors[:-1])+sep+authors[-1])
            labels.add("、".join(authors))
        for label in labels:
            signatures.setdefault((norm(label),yr[:4]),[]).append((str(rec.get("id",index)),suffix))
            known.append(label)
    first = sorted(set(known),key=lambda x:(-len(x),x))
    narrative = (re.compile(r"(?<![\w-])(?:"+"|".join(re.escape(n) for n in first)+r")\s*$",re.I) if first else None)
    ends = sentence_breaks(manuscript)
    result,issues = [],[]
    def bind(label,yr,start,stop):
        candidates = signatures.get((norm(label),yr[:4]),[])
        if yr[4:]:
            candidates = [pair for pair in candidates if pair[1].casefold()==yr[4:].casefold()]
        ids = list(dict.fromkeys(i for i,_ in candidates))
        sentence = citation_context(manuscript,start,ends)
        entry = {"source_offsets":[start,stop],"old":manuscript[start:stop],"new":manuscript[start:stop],
                 "sentence":sentence,"record_ids":ids if len(ids)==1 else [],"style":"author-year"}
        if len(ids)!=1:
            entry["candidates"]=ids
            issues.append({"offset":start,"issue":"ambiguous author-year citation" if ids else "unresolved author-year citation",
                           "author":label,"year":yr,"candidates":ids,"sentence":sentence})
        result.append(entry)
    for m in YEAR_GROUP.finditer(manuscript):
        if any(a < m.end() and b > m.start() for a,b in ignored):
            continue
        content = m[1]
        if re.fullmatch(YEAR_TOK,content.strip()):
            lead = narrative.search(manuscript[max(0,m.start()-180):m.start()]) if narrative else None
            if lead:
                bind(lead[0].strip(),content.strip(),max(0,m.start()-180)+lead.start(),m.end())
            continue
        for part in re.finditer(r"[^;；]+",content):
            fragment = LESS_LOCATOR.sub("",part[0])
            parsed = re.fullmatch(r"\s*(?:(?:see(?: also)?|e\.g\.|cf\.)[, ]+)?(.+?)\s*[,，]?\s+("+YEAR_TOK+r")\s*",fragment,re.I)
            if not parsed:
                parsed = re.fullmatch(r"\s*([^,，]+?)\s*[,，]\s*("+YEAR_TOK+r")\s*",fragment)
            if not parsed:
                continue
            label,yr = parsed[1].strip(),parsed[2]
            label = label.rstrip(",，").strip()
            if not label:
                continue
            # Unknown names are reported only for conventional comma-delimited citations.
            scholarly = ("," in fragment or "，" in fragment) and bool(re.fullmatch(
                r"(?:[A-ZÀ-ÖØ-Þ][\w’'\-]+(?:\s+(?:et al\.?|[A-ZÀ-ÖØ-Þ][\w’'\-]+))?|[\u3400-\u9fff]{2,8}等?)",label))
            if (norm(label),yr[:4]) not in signatures and not scholarly:
                continue
            offset = m.start(1)+part.start()
            bind(label,yr,offset+parsed.start(1),offset+parsed.end(2))
    return result,issues


def reconcile(records,manuscript,labels=None):
    revised,report = reconcile_numbered_and_keyed(records,manuscript,labels)
    merged,_,_,_ = groups(records)
    ignored = [m.span() for m in PROTECTED.finditer(manuscript)] + [m.span() for m,_ in keyed_groups(manuscript)]
    heading = REF_HEAD.search(manuscript)
    if heading:
        tail = NEXT_SECTION.search(manuscript,heading.end())
        ignored.append((heading.start(),tail.start() if tail else len(manuscript)))
    author_year,issues = author_year_occurrences(manuscript,merged,ignored)
    if not author_year:
        return revised,report
    previous = report["occurrences"]
    if any("style" not in o for o in previous):
        # Preserve the original printed number system, including mixed-format bibliographies.
        changed = [(o["source_offsets"],o["new"]) for o in previous if o["new"]!=o["old"] and
                   (o["old"].startswith("\\") or "@" in o["old"])]
        revised = manuscript
        for (a,b),value in sorted(changed,reverse=True):
            revised = revised[:a]+value+revised[b:]
        for o in previous:
            if "@" not in o["old"] and not o["old"].startswith("\\"):
                o["new"]=o["old"]
    rows = sorted(previous+author_year,key=lambda o:o["source_offsets"][0])
    ids = {str(r.get("id",i)):r for i,r in enumerate(merged,1)}
    cited = list(dict.fromkeys(rid for o in rows for rid in o["record_ids"]))
    for entry in report.get("cited",[]):
        rid = str(entry["record"].get("id",""))
        if rid in ids and rid not in cited:
            cited.append(rid)
    report.update(occurrences=rows,issues=report["issues"]+issues,
                  label_source="mixed_with_author_year" if previous else "author_year",
                  numbering_status="original_labels_preserved",cited=[{"number":i,"record":ids[rid]} for i,rid in enumerate(cited,1)],
                  uncited=[r for rid,r in ids.items() if rid not in cited])
    return revised,report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("records",type=Path);p.add_argument("manuscript",type=Path);p.add_argument("out",type=Path);p.add_argument("--labels")
    a=p.parse_args();text,report=reconcile(import_records(a.records),a.manuscript.read_text(encoding="utf-8"),read(a.labels) if a.labels else None)
    atomic_text(a.out/"manuscript.md",text);write(a.out/"citation-audit.json",report);write(a.out/"cited.csl.json",[r["record"] for r in report["cited"]])
