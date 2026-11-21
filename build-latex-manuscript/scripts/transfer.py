"""Insert a manuscript fragment into an existing author's TeX template, then build that project."""
import argparse
from difflib import unified_diff
import hashlib
from pathlib import Path
import re
import shutil
import tempfile

from build import FLAGS, build
from casework import atomic_text, write


def destination(root, name):
    part = Path(name)
    if part.is_absolute() or ".." in part.parts or not part.parts:
        raise ValueError("select a file inside the template")
    result = root/part
    if any(p.is_symlink() for p in (result,*result.parents) if p == root or root in p.parents):
        raise ValueError("template destinations must be ordinary files")
    return result


def insert(text, fragment, before=None, between=None):
    lines = text.splitlines(keepends=True)

    def position(marker):
        hits = [i for i,line in enumerate(lines) if line.strip()==marker.strip()]
        if not marker.strip() or len(hits)!=1:
            raise ValueError(f"expected one complete template line matching {marker!r}, found {len(hits)}")
        return hits[0]

    if between:
        left,right = position(between[0])+1,position(between[1])
        if left > right:
            raise ValueError("section boundaries are reversed or coincide")
    else:
        left = right = position(before)
    if re.search(r"(?m)^\s*\\(?:documentclass|begin\s*\{document\}|end\s*\{document\})",fragment):
        raise ValueError("select the body fragment, excluding the document preamble and end marker")
    newline = "\r\n" if "\r\n" in text else "\n"
    addition = newline.join(fragment.splitlines()) + newline
    return "".join(lines[:left]) + addition + "".join(lines[right:]), [left+1,right]


def migrate(project, target, fragment, out, main, before, between, assets, engine):
    project,out = project.resolve(),out.resolve()
    if not project.is_dir() or out == project or project in out.parents or out in project.parents:
        raise ValueError("choose separate template and output directories")
    origin = destination(project,target)
    if origin.suffix.lower() != ".tex" or not origin.is_file() or not fragment.is_file():
        raise ValueError("supply an existing TeX target and a manuscript fragment")
    original = origin.read_bytes().decode("utf-8")
    value = fragment.read_bytes()
    changed, interval = insert(original,value.decode("utf-8"),before,between)
    diff = "".join(unified_diff(original.splitlines(keepends=True),changed.splitlines(keepends=True),
                                fromfile="original/"+str(target),tofile="source/"+str(target)))
    attached = []
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)/"template"
        def exclude(directory,names):
            return [n for n in names if n.startswith(".") or (Path(directory)/n).is_symlink()]
        shutil.copytree(project,stage,ignore=exclude)
        destination(stage,target).write_bytes(changed.encode())
        for supplied,name in assets:
            src,dest = Path(supplied),destination(stage,name)
            if not src.is_file():
                raise ValueError("missing supplied asset "+src.name)
            payload = src.read_bytes()
            if dest.exists() and (not dest.is_file() or dest.read_bytes()!=payload):
                raise ValueError("asset would replace an existing template file: "+name)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(payload)
            attached.append({"path":name,"sha256":hashlib.sha256(payload).hexdigest()})
        built = build(stage,main,out,engine)
    atomic_text(out/"changes.diff",diff)
    write(out/"migration.json",{"target":str(target),"original_sha256":hashlib.sha256(original.encode()).hexdigest(),
                                "fragment":fragment.name,"fragment_sha256":hashlib.sha256(value).hexdigest(),
                                "insert_at_line":interval[0],"removed_lines":max(0,interval[1]-interval[0]+1),
                                "assets":attached,"compile_status":built["status"]})
    return built


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project",type=Path)
    parser.add_argument("target",help="actual .tex path relative to the template")
    parser.add_argument("fragment",type=Path)
    parser.add_argument("out",type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--before-line")
    group.add_argument("--between",nargs=2,metavar=("BEGIN","END"))
    parser.add_argument("--main",default="auto")
    parser.add_argument("--asset",nargs=2,action="append",default=[],metavar=("FILE","DEST"))
    parser.add_argument("--engine",choices=FLAGS)
    args = parser.parse_args()
    try:
        result = migrate(args.project,args.target,args.fragment,args.out,args.main,args.before_line,
                         args.between,args.asset,args.engine)
    except (ValueError,OSError) as exc:
        parser.exit(2,str(exc)+"\n")
    print(result["main"],result["status"])
    raise SystemExit(result["status"]!="success")
