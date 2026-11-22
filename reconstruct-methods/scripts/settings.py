"""Read experimental settings with their run, source record, unit and row or line."""
import argparse
from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import re
from casework import write

RUN_KEYS = ('run_id', 'run-id', 'run')
UNIT = r'ms|s|min|h|mm|cm|km|mV|V|Hz|kHz|MHz|Pa|kPa|K|°C|m|kg|g|%'
SETTING = re.compile(r'(?<![\w-])([A-Za-z_][\w.-]*)\s*[:=]\s*'
                     r'("[^"]*"|\x27[^\x27]*\x27|[-+.\w/%]+(?:[ \t]+(?:' + UNIT + r')(?![\w=]))?)')

def run_id(fields, inherited=None):
    for label in RUN_KEYS:
        value = fields.get(label)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            return str(value).strip()
    return inherited

def scalar_fields(data, path='', scope=None):
    if isinstance(data, dict):
        scope = run_id(data, scope)
        for name, value in data.items():
            key = str(name).replace('~','~0').replace('/','~1')
            yield from scalar_fields(value, path+'/'+key, scope)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from scalar_fields(value, path+'/'+str(index), scope)
    elif data is not None:
        value = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        yield path or '/', value, scope

def collect(root):
    observations=defaultdict(list)
    issues=[]
    def add(name,value,file,locator,scope):
        if name and value is not None:
            observations[name.casefold()].append({'name':name,'value':str(value),'file':file,'locator':locator,'run_id':scope})
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.name in {'case.json','task.md'}:
            continue
        ext=path.suffix.lower()
        if ext not in {'.json','.yml','.yaml','.csv','.tsv','.txt','.log','.cfg','.ini','.toml'}:
            continue
        rel=path.relative_to(root).as_posix()
        try:
            raw=path.read_text(encoding='utf-8-sig')
            data=None
            if ext=='.json':
                data=json.loads(raw)
            elif ext in {'.yml','.yaml'}:
                try:
                    import yaml
                except ImportError:
                    pass
                else:
                    try:
                        data=yaml.safe_load(raw)
                    except yaml.YAMLError as error:
                        issues.append({'file':rel,'reason':str(error)})
                        continue
            if data is not None:
                for loc,value,scope in scalar_fields(data):
                    add(loc.split('/')[-1],value,rel,loc,scope)
            elif ext in {'.csv','.tsv'}:
                rows=csv.DictReader(io.StringIO(raw),delimiter='\t' if ext=='.tsv' else ',')
                for lineno,row in enumerate(rows,2):
                    scope=run_id(row)
                    fields={row['name']:row['value']} if 'name' in row and 'value' in row else row
                    for name,value in fields.items():
                        if value not in ('',None):
                            add(name,value,rel,'row '+str(lineno),scope)
            else:
                for lineno,line in enumerate(raw.splitlines(),1):
                    pairs=[(m[1],m[2].strip('"\x27')) for m in SETTING.finditer(line)]
                    scope=run_id(dict(pairs))
                    for name,value in pairs:
                        add(name,value,rel,'L'+str(lineno),scope)
        except (OSError,ValueError) as exc:
            issues.append({'file':rel,'reason':str(exc)})
    candidates={}
    within=defaultdict(dict)
    for name,rows in observations.items():
        if name in RUN_KEYS:
            continue
        grouped=defaultdict(list)
        for row in rows:
            grouped[row['run_id']].append(row)
        involved=[]
        for scope,group in grouped.items():
            if len({x['value'] for x in group})>1:
                involved.extend(group)
                if scope is not None:
                    within[scope][name]=group
        # A run-specific setting can also be an override of an unscoped default.
        if None in grouped and len({x['value'] for x in rows})>1:
            involved=rows
        if involved:
            candidates[name]=involved
    return {'observations':dict(observations),'candidate_conflicts':candidates,'within_run_conflicts':dict(within),'issues':issues}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('materials',type=Path);p.add_argument('out')
    a=p.parse_args();write(a.out,collect(a.materials))
