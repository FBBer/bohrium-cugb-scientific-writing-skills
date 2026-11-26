"""Apply the original case contract to real output, preserving an editable draft for custom fields."""
import argparse
import json
from pathlib import Path
from casework import read, write, validate, contract_fields

def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", type=Path, default=Path("/input"))
    parser.add_argument("--work", type=Path, default=Path("/app/work"))
    parser.add_argument("--output", type=Path, default=Path("/app/output"))
    parser.add_argument("--fields", type=Path, help="JSON object containing case-specific results")
    return parser

def context(args):
    root, work, output = (p.resolve() for p in (args.input,args.work,args.output))
    if root==work or root==output or work==output or root in work.parents or root in output.parents:
        raise ValueError("use separate input, work and output directories")
    case=read(root/"case.json")
    if not isinstance(case,dict) or "case_id" not in case:
        raise ValueError("case.json needs its original case_id")
    work.mkdir(parents=True,exist_ok=True)
    output.mkdir(parents=True,exist_ok=True)
    task=root/"task.md"
    return root, work, output, case, task.read_text(encoding="utf-8-sig") if task.is_file() else ""

def finish(case, data, defaults, fields, work, output):
    contract=case.get("output_contract",{})
    required=contract_fields(contract)
    properties=contract.get("properties",{}) if isinstance(contract,dict) else {}
    allowed=set(required)|set(properties)
    restricted=isinstance(contract,dict) and contract.get("additionalProperties") is False
    keys=allowed if restricted else allowed|set(defaults)
    result={key:data[key] for key in sorted(keys) if key in data}
    if fields:
        extra=read(fields)
        if not isinstance(extra,dict):raise ValueError("--fields must contain an object")
        if "case_id" in extra and extra["case_id"]!=case["case_id"]:raise ValueError("source case_id cannot be changed")
        result.update(extra)
    result["case_id"]=case["case_id"]
    errors=validate(case,result)
    review={"case_id":case["case_id"],"required":required,"available":sorted(data),"errors":errors}
    write(work/"contract-review.json",review)
    write(work/"candidate.json",result)
    if errors:
        previous=output/"result.json"
        if previous.is_file():
            try:old=read(previous)
            except (ValueError,OSError):old=None
            if old is None or validate(case,old):
                if old is not None:write(work/"previous-result.json",old)
                previous.unlink(missing_ok=True)
        print("Case needs a correction in the named fields. See",work/"contract-review.json")
        return 2
    write(output/"result.json",result)
    return 0
