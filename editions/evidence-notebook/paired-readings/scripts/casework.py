"""Build a source index and validate an agent's result against the supplied case."""
import argparse
import collections
import csv
from source_records import delimited_records, json_records, lookup
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


MATH = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
ALT = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
LEVEL_TEXT = {"superscript": str.maketrans("0123456789+-−=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾"),
              "subscript": str.maketrans("0123456789+-−=()", "₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎")}


def script_text(value, level):
    if not value:
        return ""
    if re.fullmatch(r"[0-9+−=()\-]+", value):
        return value.translate(LEVEL_TEXT[level])
    return ("^(" if level == "superscript" else "_(") + value + ")"


def math_text(node):
    """Linear reading for common native Word equations; retain an explicit marker for other constructs."""
    if node is None:
        return ""
    name = node.tag.rsplit("}", 1)[-1]
    if name.endswith("Pr") or not node.tag.startswith(MATH):
        return ""
    part = lambda tag: math_text(node.find(MATH + tag))
    if name == "t":
        return node.text or ""
    if name == "f":
        return "(" + part("num") + ")/(" + part("den") + ")"
    if name in {"sSub", "sSup", "sSubSup", "sPre"}:
        low = script_text(part("sub"), "subscript")
        high = script_text(part("sup"), "superscript")
        return low + high + part("e") if name == "sPre" else part("e") + low + high
    if name == "rad":
        degree = part("deg")
        return ("root[" + degree + "]" if degree else "√") + "(" + part("e") + ")"
    if name == "d":
        def delim(tag, default):
            elem = node.find(MATH + "dPr/" + MATH + tag)
            return elem.get(MATH + "val", default) if elem is not None else default
        return delim("begChr", "(") + delim("sepChr", "|").join(math_text(e) for e in node.findall(MATH+"e")) + delim("endChr", ")")
    if name in {"oMath", "oMathPara", "r", "num", "den", "e", "sub", "sup", "deg"}:
        return "".join(math_text(child) for child in node)
    return "⟦OMML:" + name + "⟧"


def word_text(node):
    if node.tag in {W+"del", W+"moveFrom", W+"instrText", W+"delText", W+"pPr", W+"rPr"}:
        return ""
    if node.tag in {MATH+"oMath", MATH+"oMathPara"}:
        return math_text(node)
    if node.tag == ALT+"AlternateContent":
        choices = node.findall(ALT+"Choice")
        first = next((part for part in choices if part.find(".//"+MATH+"oMath") is not None), None)
        if first is None:
            first = node.find(ALT+"Fallback")
        if first is None and choices:
            first = choices[0]
        return word_text(first) if first is not None else ""
    if node.tag == W+"t":
        return node.text or ""
    if node.tag in {W+"br", W+"cr", W+"tab", W+"noBreakHyphen"}:
        return {W+"br":"\n", W+"cr":"\n", W+"tab":"\t", W+"noBreakHyphen":"‑"}[node.tag]
    content = "".join(word_text(child) for child in node)
    if node.tag == W+"r" and content:
        setting = node.find(W+"rPr/"+W+"vertAlign")
        level = setting.get(W+"val") if setting is not None else None
        if level in LEVEL_TEXT:
            return script_text(content,level)
    return content


def office_parts(path):
    with zipfile.ZipFile(path) as archive:
        if path.suffix.lower() == ".docx":
            tree = ET.fromstring(archive.read("word/document.xml"))
            note_links = collections.defaultdict(list)
            for i, p in enumerate(tree.iter(W+"p"), 1):
                for kind in ("footnote","endnote"):
                    for marker in p.iter(W+kind+"Reference"):
                        note_links[kind,marker.get(W+"id")].append(i)
                s = word_text(p)
                if s.strip():
                    yield f"word/document.xml:p{i}", s
            for table_number, table in enumerate(tree.iter(W+"tbl"), 1):
                for row_number, row in enumerate(table.findall(W+"tr"), 1):
                    before = row.find(W+"trPr/"+W+"gridBefore")
                    column = 1 + (int(before.get(W+"val", "0")) if before is not None else 0)
                    for cell in row.findall(W+"tc"):
                        span = cell.find(W+"tcPr/"+W+"gridSpan")
                        width = int(span.get(W+"val", "1")) if span is not None else 1
                        # Record the physical cell once. A vertical merge continuation has no new value.
                        end = f"-C{column+width-1}" if width > 1 else ""
                        location = f"word/document.xml:tbl{table_number}:R{row_number}:C{column}{end}"
                        paragraphs_in_cell = cell.findall(W+"p")
                        cell_text = "\n".join(word_text(p) for p in paragraphs_in_cell).strip()
                        if cell_text:
                            yield location, cell_text
                        column += width
            for notes in ("footnotes", "endnotes"):
                member = "word/" + notes + ".xml"
                if member not in archive.namelist():
                    continue
                for note in ET.fromstring(archive.read(member)):
                    if note.get(W+"type") in {"separator", "continuationSeparator", "continuationNotice"}:
                        continue
                    number = note.get(W+"id")
                    for i, para in enumerate(note.iter(W+"p"), 1):
                        text = word_text(para)
                        if text.strip():
                            yield f"{member}:{number}:p{i}", text
                            for owner in note_links[notes[:-1],number]:
                                yield f"word/document.xml:p{owner}/{notes[:-1]}:{number}:p{i}", text
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


def prepare(input_dir, work, *, reading_layout=False):
    root = Path(input_dir).resolve()
    work = Path(work).resolve()
    if not root.is_dir() or work == root:
        raise ValueError("choose an existing materials folder and a separate output folder")
    case_file = root/"case.json"
    case = read(case_file) if case_file.is_file() else {}
    if not isinstance(case, dict):
        raise ValueError("case.json must contain an object")
    rows, files, issues, records = [], [], [], []

    def append(source, location, text):
        if not text.strip():
            return
        anchor = source + "#" + location
        rows.append({"id": "s"+hashlib.sha256(anchor.encode()).hexdigest()[:15],
                     "source":source, "location":location, "text":text})
        return rows[-1]["id"]

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or (root in work.parents and work in path.parents):
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
                records.extend(json_records(data, rel, append))
            elif ext in {".csv", ".tsv", ".jsonl"}:
                raw = path.read_text(encoding="utf-8-sig")
                for loc, para in paragraphs(raw):
                    append(rel, loc, para)
                if ext == ".jsonl":
                    for line_number, line in enumerate(raw.splitlines(), 1):
                        if not line.strip():
                            continue
                        try:
                            document = json.loads(line)
                        except ValueError as error:
                            issues.append({"file":rel, "location":f"L{line_number}", "reason":str(error)})
                            continue
                        records.extend(json_records(document, rel, append, f"L{line_number}:"))
                else:
                    records.extend(delimited_records(path, rel, append))
            elif ext == ".pdf":
                if reading_layout:
                    from paper_structure import pdf_blocks
                    pages = pdf_blocks(path)
                    if pages is not None:
                        for n, blocks in pages:
                            if not blocks:
                                issues.append({"file":rel,"location":f"p{n}","reason":"no text layer; render/OCR page"})
                            for block in blocks:
                                append(rel, block["location"], block["text"])
                                rows[-1].update({k:block[k] for k in ("bbox","page","story","heading_level") if k in block})
                        continue
                for n, text in pdf_parts(path):
                    if not text.strip():
                        issues.append({"file":rel,"location":f"p{n}", "reason":"no text layer; render/OCR page"})
                    for loc, para in paragraphs(text):
                        append(rel, f"p{n}:{loc}", para)
            elif ext in {".docx", ".pptx"}:
                styles = {}
                if reading_layout and ext == ".docx":
                    from paper_structure import word_styles
                    styles = word_styles(path)
                for loc, para in office_parts(path):
                    append(rel, loc, para)
                    if loc in styles:
                        rows[-1].update(styles[loc])
            elif ext == ".xlsx":
                for loc, value in spreadsheet_parts(path, issues, rel):
                    append(rel, loc, value)
            elif ext in TEXT:
                raw = path.read_text(encoding="utf-8-sig")
                for loc, para in paragraphs(raw):
                    append(rel, loc, para)
            else:
                issues.append({"file":rel,"reason":"binary/other format; open in its native reader"})
        except (OSError, ValueError, ImportError, KeyError, RuntimeError, ET.ParseError, zipfile.BadZipFile, csv.Error, subprocess.SubprocessError) as exc:
            issues.append({"file":rel,"reason":str(exc)})
    index = {"case_id":case.get("case_id"),"files":files,"sources":rows,"records":records,"issues":issues}
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


def find_sources(index, terms, source=None, location="", limit=12):
    """Return literal, source-located excerpts without joining unrelated evidence."""
    if not terms or any(not term.strip() for term in terms) or limit < 1:
        raise ValueError("Supply a nonempty search term and a positive limit")
    patterns = [re.compile(re.escape(term), re.I) for term in terms]
    matches, total = [], 0
    for row in index["sources"]:
        if (source is not None and row["source"] != source) or not row["location"].startswith(location):
            continue
        hits = [pattern.search(row["text"]) for pattern in patterns]
        if not all(hits):
            continue
        total += 1
        if len(matches) >= limit:
            continue
        windows = []
        for start, end in sorted((max(0, hit.start()-64), min(len(row["text"]), hit.end()+64)) for hit in hits):
            if windows and start <= windows[-1][1]:
                windows[-1][1] = max(end, windows[-1][1])
            else:
                windows.append([start, end])
        matches.append({"id":row["id"], "source":row["source"], "location":row["location"],
                        "excerpts":[{"quote":row["text"][a:b], "start":a, "end":b} for a,b in windows]})
    return {"case_id":index.get("case_id"), "total":total, "matches":matches}


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
    if "properties" in contract or "$schema" in contract:
        # In JSON Schema, properties are optional unless required explicitly.
        return []
    for key in ("required_fields", "fields", "result_fields", "output_fields"):
        if key in contract:
            fields = contract[key]
            if isinstance(fields, list):
                fields = [v for v in fields if not isinstance(v, dict) or v.get("required") is not False]
            return field_names(fields)
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
                validator = jsonschema.validators.validator_for(contract)
                for err in validator(contract).iter_errors(result):
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
    p=sub.add_parser("find",help="find exact evidence and its location in the source index")
    p.add_argument("terms",nargs="+")
    p.add_argument("--index",default="/app/work/sources.json")
    p.add_argument("--source",help="exact path of one indexed input")
    p.add_argument("--location",default="",help="prefix of an indexed position")
    p.add_argument("--limit",type=int,default=12)
    p=sub.add_parser("rows",help="look up values within a single JSON record or a single CSV/TSV observation")
    p.add_argument("--index",default="/app/work/sources.json")
    p.add_argument("--source",required=True)
    p.add_argument("--where",nargs=2,action="append",default=[],metavar=("FIELD","VALUE"))
    p.add_argument("--select",action="append",default=[],metavar="FIELD")
    p.add_argument("--limit",type=int,default=12)
    p=sub.add_parser("check")
    p.add_argument("--case",default="/input/case.json")
    p.add_argument("--result",default="/app/output/result.json")
    p=sub.add_parser("deliver",help="assemble a result from the case fields and real output files")
    p.add_argument("--case",default="/input/case.json")
    p.add_argument("--result",default="/app/output/result.json")
    p.add_argument("--fields",help="JSON object containing the fields written for this case")
    p.add_argument("--json",nargs=3,action="append",default=[],metavar=("DEST","FILE","POINTER"))
    p.add_argument("--text",nargs=2,action="append",default=[],metavar=("DEST","FILE"))
    p.add_argument("--file",nargs=2,action="append",default=[],metavar=("DEST","FILE"))
    args=cli.parse_args()
    if args.op=="index":
        index=prepare(args.input,args.work)
        print(json.dumps({"case_id":index["case_id"],"files":len(index["files"]),"anchors":len(index["sources"]),"issues":index["issues"]},ensure_ascii=False))
    elif args.op=="rows":
        try:
            print(json.dumps(lookup(read(args.index),args.source,args.where,args.select,args.limit),ensure_ascii=False))
        except ValueError as error:
            cli.exit(1,str(error)+"\n")
    elif args.op=="find":
        try:
            print(json.dumps(find_sources(read(args.index),args.terms,args.source,args.location,args.limit),ensure_ascii=False))
        except ValueError as error:
            cli.exit(1,str(error)+"\n")
    elif args.op=="deliver":
        from delivery import assemble
        try:
            result = assemble(args.case, args.result, args.fields, args.json, args.text, args.file)
        except (OSError, ValueError, KeyError, IndexError) as error:
            cli.exit(1, str(error)+"\n")
        print(str(result))
    else:
        errors=validate(read(args.case),read(args.result))
        print(json.dumps({"contract_errors":errors},ensure_ascii=False))
        raise SystemExit(bool(errors))

if __name__=="__main__":
    main()
