"""Place author-selected references at identified sentences and retain the source offsets."""
import argparse
from collections import Counter
from pathlib import Path
import re

from casework import atomic_text, read, write
from citations import groups, import_records, PROTECTED
from passages import locate


def place(text, library, plan, index=None):
    merged, mapping, _, _ = groups(library)
    blocks = {r["id"]:r for r in (index or {}).get("sources",[])}
    protected = [m.span() for m in PROTECTED.finditer(text)]
    source = {"source":"manuscript","text":text,"location":"document"}
    accepted, issues = [],[]
    for i,item in enumerate(plan["placements"],1):
        try:
            if item.get("style","pandoc") not in {"pandoc","latex"}:
                raise ValueError("select pandoc or latex")
            selection = locate(source,item)
            left,right = selection["start"],selection["end"]
            # Formulas, code and links can occur inside a sentence. Only the insertion point must be prose.
            punctuation = re.search(r"[.!?。！？]+[”’\x22')）]*$",text[left:right])
            at = left + punctuation.start() if punctuation else right
            if any(first <= at < last for first,last in protected):
                raise ValueError("selected insertion point lies in a formula, code or link")
            original_ids = item.get("records",[])
            if not isinstance(original_ids,list) or not original_ids or any(r not in mapping for r in original_ids):
                raise ValueError("select existing reference-library IDs")
            keys = list(dict.fromkeys(str(merged[mapping[r]].get("id",r)) for r in original_ids))
            if any(not re.fullmatch(r"[\w.:/+_-]+",k) for k in keys):
                raise ValueError("use citation keys valid in Pandoc or TeX")
            support = []
            for ev in item.get("support",[]):
                if ev.get("record") not in original_ids or ev.get("id") not in blocks:
                    raise ValueError("evidence needs the selected record ID and an indexed source block")
                support.append({"record":ev["record"],**locate(blocks[ev["id"]],ev)})
            if item.get("style") == "latex":
                marker = r"~\cite{" + ",".join(keys) + "}"
            else:
                marker = (" " if at and not text[at-1].isspace() else "")+"["+"; ".join("@"+k for k in keys)+"]"
            accepted.append({"placement":i,"at":at,"quote":item["quote"],"source_offsets":[left,right],
                             "record_ids":keys,"marker":marker,"support":support})
        except (KeyError,ValueError,TypeError) as exc:
            issues.append({"placement":i,"reason":str(exc)})
    counts = Counter(r["at"] for r in accepted)
    edits = []
    for row in accepted:
        if counts[row["at"]] > 1:
            issues.append({"placement":row["placement"],"reason":"combine references at one sentence into a single placement"})
        elif text[max(0,row["at"]-len(row["marker"])):row["at"]] == row["marker"] or text.startswith(row["marker"],row["at"]):
            row["applied"] = False
            edits.append(row)
        else:
            row["applied"] = True
            edits.append(row)
    result = text
    for row in sorted(edits,key=lambda r:r["at"],reverse=True):
        if row["applied"]:
            at = row["at"]
            result = result[:at] + row["marker"] + result[at:]
    return result,{"placements":edits,"unresolved":issues}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library",type=Path)
    parser.add_argument("manuscript",type=Path)
    parser.add_argument("plan",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--sources",type=Path)
    args = parser.parse_args()
    original = args.manuscript.read_text(encoding="utf-8")
    revised,report = place(original,import_records(args.library),read(args.plan),
                           read(args.sources) if args.sources else None)
    dest = args.out/("manuscript-cited"+args.manuscript.suffix)
    if dest.resolve() == args.manuscript.resolve():
        parser.exit(2,"choose a separate output for the cited manuscript\n")
    atomic_text(dest,revised)
    write(args.out/"placements.json",report)
    print(sum(x["applied"] for x in report["placements"]),"insertions,",len(report["unresolved"]),"unresolved")
    raise SystemExit(bool(report["unresolved"]))
