"""Build a source index and validate an agent's result against the supplied case."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

TEXT = {".txt", ".md", ".tex", ".bib", ".ris", ".enw", ".csv", ".tsv", ".yaml", ".yml",
        ".log", ".jsonl", ".xml", ".html", ".py", ".toml", ".cfg", ".ini", ".rst"}
META = {"case_id", "task", "task_md", "task_description", "instructions", "output_contract",
        "rubric", "requirements", "expected_artifacts", "evaluation", "domain_label"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
        temp = f.name
    os.replace(temp, path)


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(text)
        temp = f.name
    os.replace(temp, path)


def paragraphs(text):
    lines = text.splitlines()
    start, part = 1, []
    for n, line in enumerate(lines + [""], 1):
        if line.strip():
            if not part:
                start = n
            part.append(line)
        elif part:
            yield f"L{start}-{n-1}", "\n".join(part)
            part = []


def pointer(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from pointer(child, path + "/" + escaped)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from pointer(child, path + "/" + str(i))
    elif value is not None:
        yield path or "/", value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def pdf_parts(path):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            pymupdf = None
    if pymupdf is not None:
        with pymupdf.open(path) as doc:
            if doc.needs_pass:
                raise ValueError("encrypted PDF, source access needed")
            for n, page in enumerate(doc, 1):
                yield n, page.get_text("text", sort=True)
    elif shutil.which("pdftotext"):
        run = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=100)
        if run.returncode:
            raise ValueError(run.stderr.decode(errors="replace")[:300])
        for n, s in enumerate(run.stdout.decode("utf-8").rstrip("\f").split("\f"), 1):
            yield n, s
    else:
        from pypdf import PdfReader
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("encrypted PDF, source access needed")
        for n, page in enumerate(reader.pages, 1):
            yield n, page.extract_text() or ""


def office_parts(path):
    with zipfile.ZipFile(path) as archive:
        if path.suffix.lower() == ".docx":
            tree = ET.fromstring(archive.read("word/document.xml"))
            for i, p in enumerate(tree.iter(W+"p"), 1):
                s = "".join(t.text or "" for t in p.iter(W+"t"))
                if s.strip():
                    yield f"word/document.xml:p{i}", s
            return
        if path.suffix.lower() == ".pptx":
            for member in sorted(archive.namelist()):
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", member):
                    root = ET.fromstring(archive.read(member))
                    for i,p in enumerate(root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}p"),1):
                        s = "".join(t.text or "" for t in p.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"))
                        if s.strip():
                            yield f"{member}:p{i}",s


def spreadsheet_parts(path, issues, source):
    """Index stored cell values and formulas separately, without calculating the workbook."""
    sheet_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

    def rich_text(element):
        # Phonetic guides are annotations, not additional characters in the cell.
        return "".join(node.text or "" for node in element.findall(sheet_ns + "t") +
                       element.findall(sheet_ns + "r/" + sheet_ns + "t"))

    def next_column(name):
        letters = list(name)
        while letters and letters[-1] == "Z":
            letters.pop()
        if not letters:
            return "A" * (len(name) + 1)
        letters[-1] = chr(ord(letters[-1]) + 1)
        return "".join(letters) + "A" * (len(name) - len(letters))

    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {}
        strings = []
        formats = []
        for relation in relations:
            if relation.get("TargetMode") == "External":
                continue
            name = posixpath.normpath(posixpath.join("xl", relation.attrib["Target"])).lstrip("/")
            if relation.get("Type", "").endswith("/worksheet"):
                targets[relation.attrib["Id"]] = name
            elif relation.get("Type", "").endswith("/sharedStrings"):
                table = ET.fromstring(archive.read(name))
                strings = [rich_text(item) for item in table.findall(sheet_ns + "si")]
            elif relation.get("Type", "").endswith("/styles"):
                styles = ET.fromstring(archive.read(name))
                codes = {"9": "0%", "10": "0.00%"}
                for entry in styles.findall(sheet_ns + "numFmts/" + sheet_ns + "numFmt"):
                    codes[entry.attrib["numFmtId"]] = entry.attrib["formatCode"]
                formats = [codes.get(entry.get("numFmtId")) for entry in
                           styles.findall(sheet_ns + "cellXfs/" + sheet_ns + "xf")]

        for sheet in workbook.iter(sheet_ns + "sheet"):
            member = targets.get(sheet.get(rel_ns + "id"))
            if not member:
                continue
            title = "'" + sheet.attrib["name"].replace("'", "''") + "'!"
            row_number = 0
            with archive.open(member) as stream:
                for _, row in ET.iterparse(stream, events=("end",)):
                    if row.tag != sheet_ns + "row":
                        continue
                    row_number = int(row.get("r", row_number + 1))
                    column = "A"
                    for cell in row.findall(sheet_ns + "c"):
                        address = cell.get("r", column + str(row_number))
                        position = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", address)
                        if position is None:
                            issues.append({"file": source, "location": title, "reason": "invalid cell address " + address})
                            continue
                        column = next_column(position[1])
                        location = title + address
                        kind = cell.get("t", "n")
                        value = cell.findtext(sheet_ns + "v")
                        formula = cell.find(sheet_ns + "f")
                        if formula is not None:
                            if formula.text:
                                yield location + ":formula", "=" + formula.text
                            if value in (None, ""):
                                issues.append({"file": source, "location": location,
                                               "reason": "formula has no stored result; recalculate in the original workbook"})
                                continue
                            location += ":cached"
                        if kind == "s" and value is not None:
                            if not value.isdecimal() or int(value) >= len(strings):
                                issues.append({"file": source, "location": location, "reason": "invalid shared-string index"})
                                continue
                            value = strings[int(value)]
                        elif kind == "inlineStr":
                            content = cell.find(sheet_ns + "is")
                            value = rich_text(content) if content is not None else None
                        elif kind == "b" and value in {"0", "1"}:
                            value = "TRUE" if value == "1" else "FALSE"
                        elif kind == "e":
                            issues.append({"file": source, "location": location, "reason": "Excel error " + (value or "")})
                            continue
                        if value is not None and value.strip():
                            yield location, value
                            style = cell.get("s", "0")
                            if kind == "n" and style.isdecimal() and int(style) < len(formats) and formats[int(style)]:
                                yield title + address + ":format", formats[int(style)]
                    row.clear()


def prepare(input_dir, work):
    root = Path(input_dir)
    case = read(root/"case.json")
    rows, files, issues = [], [], []

    def append(source, location, text):
        if not text.strip():
            return
        anchor = source + "#" + location
        rows.append({"id": "s"+hashlib.sha256(anchor.encode()).hexdigest()[:15],
                     "source":source, "location":location, "text":text})

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        files.append({"path":rel, "bytes":path.stat().st_size})
        if path == root/"task.md":
            continue
        try:
            ext = path.suffix.lower()
            if ext == ".json":
                data = case if path == root/"case.json" else read(path)
                if path == root/"case.json":
                    data = {k:v for k,v in data.items() if k not in META}
                for loc, val in pointer(data):
                    append(rel, loc, val)
            elif ext == ".pdf":
                for n, text in pdf_parts(path):
                    if not text.strip():
                        issues.append({"file":rel,"location":f"p{n}", "reason":"no text layer; render/OCR page"})
                    for loc, para in paragraphs(text):
                        append(rel, f"p{n}:{loc}", para)
            elif ext in {".docx", ".pptx"}:
                for loc, para in office_parts(path):
                    append(rel, loc, para)
            elif ext == ".xlsx":
                for loc, value in spreadsheet_parts(path, issues, rel):
                    append(rel, loc, value)
            elif ext in TEXT:
                raw = path.read_text(encoding="utf-8-sig")
                for loc, para in paragraphs(raw):
                    append(rel, loc, para)
            else:
                issues.append({"file":rel,"reason":"binary/other format; open in its native reader"})
        except (OSError, ValueError, ImportError, KeyError, RuntimeError, ET.ParseError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
            issues.append({"file":rel,"reason":str(exc)})
    index = {"case_id":case.get("case_id"),"files":files,"sources":rows,"issues":issues}
    write(Path(work)/"sources.json", index)
    return index


def check_evidence(evidence, sources):
    found = {s["id"]:s for s in sources}
    failures = []
    for i, ev in enumerate(evidence):
        src = found.get(ev.get("id"))
        quote = ev.get("quote")
        if not src or not isinstance(quote,str) or not quote or quote not in src["text"]:
            failures.append(f"evidence[{i}] has unknown anchor or nonliteral quote")
    return failures


def field_names(value):
    if isinstance(value, dict):
        return list(value)
    if isinstance(value, list):
        return [v if isinstance(v,str) else v.get("name",v.get("field",v.get("key"))) for v in value if isinstance(v,(str,dict))]
    return []


def contract_fields(contract):
    if isinstance(contract, list):
        return field_names(contract)
    if not isinstance(contract,dict):
        return []
    if "required" in contract and isinstance(contract["required"],list):
        return field_names(contract["required"])
    for key in ("required_fields", "fields", "properties", "result_fields", "output_fields"):
        if key in contract:
            return field_names(contract[key])
    descriptions = {"type","description","format","required_artifacts","artifacts","files","notes","example",
                    "additionalProperties","$schema","$defs","definitions","title"}
    return [k for k in contract if k not in descriptions]


def validate(case, result):
    errors=[]
    if not isinstance(result,dict):
        return ["result must be a JSON object"]
    if "case_id" not in case or result.get("case_id") != case["case_id"]:
        errors.append("case_id missing or differs from original")
    contract = case.get("output_contract",{})
    for k in contract_fields(contract):
        if k and k not in result:
            errors.append(f"missing contract field {k}")
    if isinstance(contract,dict) and ("properties" in contract or "$schema" in contract):
        try:
            import jsonschema
        except ImportError:
            from schema_check import check
            errors.extend(check(contract,result))
        else:
            try:
                for err in jsonschema.Draft202012Validator(contract).iter_errors(result):
                    errors.append(f"{list(err.absolute_path)} {err.message}")
            except (TypeError, ValueError, jsonschema.exceptions.SchemaError) as exc:
                errors.append("inspect nonstandard contract: "+str(exc))
    return errors


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest="op",required=True)
    p=sub.add_parser("index")
    p.add_argument("--input",default="/input")
    p.add_argument("--work",default="/app/work")
    p=sub.add_parser("check")
    p.add_argument("--case",default="/input/case.json")
    p.add_argument("--result",default="/app/output/result.json")
    args=cli.parse_args()
    if args.op=="index":
        index=prepare(args.input,args.work)
        print(json.dumps({"case_id":index["case_id"],"files":len(index["files"]),"anchors":len(index["sources"]),"issues":index["issues"]},ensure_ascii=False))
    else:
        errors=validate(read(args.case),read(args.result))
        print(json.dumps({"contract_errors":errors},ensure_ascii=False))
        raise SystemExit(bool(errors))

if __name__=="__main__":
    main()
