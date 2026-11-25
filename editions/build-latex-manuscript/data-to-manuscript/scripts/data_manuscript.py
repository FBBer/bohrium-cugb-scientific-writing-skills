"""Regenerate inline measurements and table rows from the same CSV, then build the editable manuscript."""
import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
from build import build
from casework import write

ESC={"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#","_":r"\_","{":r"\{","}":r"\}","~":r"\textasciitilde{}","^":r"\textasciicircum{}"}
def tex(s):
    return "".join(ESC.get(c,c) for c in s)

def fixed(raw,places):
    if not isinstance(places,int) or not 0<=places<=12:
        raise ValueError("decimal places must be an integer from 0 to 12")
    number=Decimal(raw)
    if not number.is_finite():
        raise ValueError("non-finite manuscript value")
    v=number.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
    return format(abs(v) if v==0 else v,"f")

def inside(root,relative):
    result=(root/relative).resolve()
    if not result.is_relative_to(root):raise ValueError("file must be inside the source project")
    return result

def compile_data(project,spec,out):
    project=project.resolve();out=out.resolve()
    if project==out or project in out.parents:raise ValueError("choose output outside the source tree")
    data=inside(project,spec["csv"])
    main=inside(project,spec["main"])
    if not main.is_file():raise ValueError("missing main manuscript")
    generated=inside(project,spec["generated"])
    if generated.exists() or generated.suffix!=".tex":
        raise ValueError("choose a new .tex file for generated measurements")
    header=["% Generated from "+Path(spec["csv"]).name+" by GPT-6.2Astra."]
    fields=[];rows=[];keys=set()
    with data.open(encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream,delimiter="\t" if data.suffix==".tsv" else ",")
        cols=spec["columns"]
        if not set(cols.values())<=set(reader.fieldnames or []):raise ValueError("missing source column")
        for line in reader:
            key=line[cols["id"]]
            if not re.fullmatch("[A-Za-z][A-Za-z0-9-]*",key) or key in keys:raise ValueError("duplicate or invalid measurement key "+key)
            keys.add(key)
            raw=line[cols["value"]];unit=line[cols["unit"]]
            value=fixed(raw,spec["places"]); label=line[cols["label"]]
            raw_error=line.get(cols.get("uncertainty",""),"").strip()
            error=fixed(raw_error,spec["places"]) if raw_error else None
            if raw_error and Decimal(raw_error)<0:raise ValueError("negative reported uncertainty")
            shown=value + (r"\,\pm\,"+error if error is not None else "")
            header.append(r"\expandafter\def\csname obs@"+key+r"\endcsname{\ensuremath{"+shown+r"}\,\textnormal{"+tex(unit)+"}}")
            rows.append(tex(label)+r" & \ObsValue{"+key+r"} \\")
            fields.append(dict(id=key,label=label,file=spec["csv"],row=reader.line_num,value_column=cols["value"],
                               raw=raw,uncertainty_raw=raw_error,display=value,uncertainty=error,unit=unit))
    if not fields:raise ValueError("no measurement rows")
    header.extend([r"\newcommand{\ObsValue}[1]{\ifcsname obs@#1\endcsname\csname obs@#1\endcsname\else\PackageError{observations}{Unknown observation #1}{}\fi}",
                   r"\newcommand{\ObsTableRows}{"+"\n"+"\n".join(rows)+"\n}"])
    sources=[p for p in project.rglob("*.tex") if p.is_file() and not p.is_symlink()]
    original="\n".join(re.sub(r"(?<!\\)%[^\n]*","",p.read_text(encoding="utf-8")) for p in sources)
    used=re.findall(r"\\ObsValue\{([A-Za-z][A-Za-z0-9-]*)\}",original)
    if set(used)-keys:raise ValueError("unknown cited measurement: "+", ".join(sorted(set(used)-keys)))
    if not used and r"\ObsTableRows" not in original:raise ValueError("manuscript has no linked measurement or table")
    with tempfile.TemporaryDirectory() as tmp:
        editable=Path(tmp)/"project"
        shutil.copytree(project,editable,ignore=shutil.ignore_patterns(".git","__pycache__",".DS_Store"),symlinks=True)
        for f in editable.rglob("*"):
            if f.is_symlink():raise ValueError("provide the actual project resources in place of symbolic links")
        fresh=editable/generated.relative_to(project);fresh.parent.mkdir(parents=True,exist_ok=True)
        fresh.write_text("\n".join(header)+"\n",encoding="utf-8")
        report=build(editable,spec["main"],out,spec.get("engine"),spec.get("workdir"))
    write(out/"measurement-sources.json",dict(author="GPT-6.2Astra",file=spec["csv"],sha256=sha256(data.read_bytes()).hexdigest(),
          rounding="half-up",decimal_places=spec["places"],inline_keys=used,records=fields,build_status=report["status"]))
    return report
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project",type=Path);parser.add_argument("spec",type=Path);parser.add_argument("output",type=Path)
    a=parser.parse_args()
    try:
        report=compile_data(a.project,json.loads(a.spec.read_text(encoding="utf-8")),a.output)
    except (KeyError,OSError,ValueError,InvalidOperation) as e:parser.exit(2,str(e)+"\n")
    print(report["status"],report["diagnostics"][:3])
    raise SystemExit(report["status"]!="success")
