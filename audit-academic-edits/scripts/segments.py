"""Select a manuscript's paragraphs from its source index, in original order."""
import argparse
from pathlib import Path
import re
from casework import read, write


def segments(index, name, field=None, notes=False):
    suffix = Path(name).suffix.lower()
    rows = [item for item in index["sources"] if item["source"] == name]
    if suffix == ".docx":
        rows = [item for item in rows if re.fullmatch(r"word/document\.xml:p\d+",item["location"])
                or (notes and re.match(r"word/(?:foot|end)notes\.xml",item["location"]))]
    elif suffix in {".json", ".jsonl", ".csv", ".tsv"}:
        if not field:
            raise ValueError("choose the manuscript text field or column with --field")
        ids = [f["id"] for r in index.get("records",[]) if r["source"] == name
               for f in r["fields"] if f["field"] == field]
        by_id = {item["id"]:item for item in rows}
        rows = [by_id[key] for key in ids]
    if not rows:
        raise ValueError("no manuscript segments at this source and field")
    return {"source":name, "segments":[{"id":s["id"], "location":s["location"], "text":s["text"]} for s in rows]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("index",type=Path)
    p.add_argument("source")
    p.add_argument("out",type=Path)
    p.add_argument("--field")
    p.add_argument("--notes",action="store_true",help="also include Word note bodies after the main text")
    a = p.parse_args()
    result = segments(read(a.index),a.source,a.field,a.notes)
    write(a.out,result)
    print(len(result["segments"]), "source segments")
