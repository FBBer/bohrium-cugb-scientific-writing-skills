"""Stage an editable TeX project, compile it and retain a fresh PDF and its diagnostics."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from casework import atomic_text, write


GENERATED = (".aux", ".log", ".out", ".toc", ".bcf", ".blg", ".lof", ".lot", ".fls",
             ".fdb_latexmk", ".synctex.gz", ".run.xml", ".nav", ".snm", ".xdv")
DIAGNOSTIC = re.compile(
    r"^! |:[0-9]+: |undefined (?:references|citations)|(?:Citation|Reference) .+ undefined|"
    r"multiply.defined|Overfull \\[hv]box|Missing character:|Rerun to get|Please \(re\)run|"
    r"^LaTeX Error|Emergency stop", re.I)
MAGIC = re.compile(r"(?im)^\s*%\s*!\s*TEX\s+(?:TS-)?program\s*=\s*((?:pdf|xe|lua)latex)\b")
FLAGS = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}
ENGINE_NAMES = {"xetex": "xelatex", "xelatex": "xelatex", "luatex": "lualatex", "lualatex": "lualatex"}
MARKER = "build-latex-manuscript\n"


def engine_for(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    directive = MAGIC.search(text)
    if directive:
        return directive[1].lower()
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    if re.search(r"\\(?:usepackage|RequirePackage|documentclass)(?:\[[^\]]*\])?\{[^}]*?(?:luacode|luatexja)", text):
        return "lualatex"
    if (re.search(r"\\(?:usepackage|RequirePackage|documentclass)(?:\[[^\]]*\])?\{[^}]*?(?:fontspec|xeCJK|ctex|unicode-math)", text)
            or re.search("[\u3400-\u9fff]", text)):
        return "xelatex"
    return "pdflatex"


def required_engine(log, current):
    # Read an actual TeX diagnostic, including messages split across package-prefixed lines.
    message = re.sub(r"\s+", " ", re.sub(r"(?m)^\([\w.-]+\)\s*", "", log))
    engine = r"(Xe(?:La)?TeX|Lua(?:La)?TeX)"
    match = re.search(r"\brequires?\s+(?:either\s+)?" + engine + r"(?:\s+or\s+" + engine + r")?\b", message, re.I)
    if not match:
        match = re.search(r"\b" + engine + r"\s+is required\b", message, re.I)
    if not match:
        match = re.search(r"\b(?:re)?compile\s+(?:with|using)\s+" + engine + r"\b", message, re.I)
    if match:
        for name in match.groups():
            if name:
                candidate = ENGINE_NAMES[name.lower()]
                if candidate != current and shutil.which(candidate):
                    return candidate, match.group(0)
    return None, None


def invoke(argv, cwd, records, env):
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=125, check=False)
        output = result.stdout.decode("utf-8", errors="replace")
        code = result.returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        code, output = 124, str(error)
    records.append({"argv": argv, "exit": code, "tail": output.splitlines()[-20:]})
    return code, output


def manual_compile(tool, main, cwd, records, env):
    before = bibliography_signature = None
    stem = main.stem
    for _ in range(6):
        rc, output = invoke([tool, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error",
                             "-file-line-error", main.as_posix()], cwd, records, env)
        if rc:
            return rc, output, False
        aux, bcf = cwd / (stem + ".aux"), cwd / (stem + ".bcf")
        auxtext = aux.read_text(errors="replace") if aux.exists() else ""
        if bcf.exists() or "\\bibdata" in auxtext:
            signature = (bcf.read_bytes() if bcf.exists() else
                         "\n".join(line for line in auxtext.splitlines()
                                   if line.startswith(("\\citation", "\\bibdata", "\\bibstyle"))).encode())
            if signature != bibliography_signature:
                rc, output = invoke(["biber" if bcf.exists() else "bibtex", stem], cwd, records, env)
                if rc:
                    return rc, output, False
                bibliography_signature, before = signature, None
                continue
        now = {p.relative_to(cwd): hashlib.sha256(p.read_bytes()).digest()
               for p in cwd.rglob("*") if p.is_file() and p.suffix in {".aux", ".toc", ".bbl", ".out", ".lof", ".lot"}}
        if now == before:
            return rc, output, True
        before = now
    return rc, output, False


def compile_once(tool, main, source, pdf):
    records = []
    env = dict(os.environ, openout_any="p", openin_any="p", shell_escape="f")
    with tempfile.TemporaryDirectory() as temporary:
        cwd = Path(temporary) / "project"
        shutil.copytree(source, cwd)
        if not shutil.which(tool):
            rc, output, stable = 127, tool + " not installed", False
        elif shutil.which("latexmk"):
            argv = ["latexmk", "-norc", FLAGS[tool], "-no-shell-escape", "-interaction=nonstopmode",
                    "-halt-on-error", "-file-line-error", main.as_posix()]
            rc, output = invoke(argv, cwd, records, env)
            stable = rc == 0
        else:
            rc, output, stable = manual_compile(tool, main, cwd, records, env)
        logfile = cwd / (main.stem + ".log")
        log = logfile.read_text(errors="replace") if logfile.is_file() else output
        built = cwd / (main.stem + ".pdf")
        if rc == 0 and built.is_file():
            with built.open("rb") as stream:
                if stream.read(5) == b"%PDF-":
                    shutil.copy2(built, pdf)
    return rc, stable, records, log


def build(project, main, out, engine=None):
    project, out, rel = project.resolve(), out.resolve(), Path(main)
    if rel.is_absolute() or ".." in rel.parts or not (project / rel).is_file():
        raise ValueError("main must be a file inside the source project")
    if out == project or project in out.parents or out in project.parents:
        raise ValueError("source and output directories must be separate")
    if engine is not None and engine not in FLAGS:
        raise ValueError("unknown engine")

    source, pdf, marker = out / "source", out / "manuscript.pdf", out / ".build-output"
    reserved = (source, pdf, marker, out / "compile.log", out / "build.json")
    if any(p.exists() or p.is_symlink() for p in reserved):
        if not marker.is_file() or marker.is_symlink() or marker.read_text() != MARKER:
            raise ValueError("choose a fresh output directory; existing manuscript or build files belong to another project")
    out.mkdir(parents=True, exist_ok=True)
    atomic_text(marker, MARKER)
    if pdf.exists():
        pdf.unlink()
    if source.exists():
        shutil.rmtree(source)
    originhash = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if not path.is_file() or path.is_symlink() or any(p.startswith(".") for p in relative.parts):
            continue
        if path.name.endswith(GENERATED) or relative == rel.with_suffix(".pdf"):
            continue
        dest = source / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        originhash[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    main_source = source / rel
    pinned = bool(engine or MAGIC.search(main_source.read_text(encoding="utf-8", errors="replace")))
    tool = engine or engine_for(main_source)
    rc, stable, records, log = compile_once(tool, rel, source, pdf)
    attempts = [{"engine": tool, "exit": rc}]
    final_records = records
    if rc and not pinned:
        alternative, reason = required_engine(log, tool)
        if alternative:
            attempts[0]["diagnostic"] = reason
            tool = alternative
            rc, stable, final_records, log = compile_once(tool, rel, source, pdf)
            records.extend(final_records)
            attempts.append({"engine": tool, "exit": rc})
    atomic_text(out / "compile.log", log)
    issues = [s.strip() for s in log.splitlines() if DIAGNOSTIC.search(s)]
    for record in final_records:
        if record["exit"]:
            issues.extend(record["tail"][-5:])
    if rc:
        issues.append("compiler exited " + str(rc))
    if not stable:
        issues.append("convergence not established")
    if not pdf.is_file():
        issues.append("no successful fresh PDF")
    version = None
    if shutil.which(tool):
        version_lines = subprocess.run([tool, "--version"], capture_output=True, text=True).stdout.splitlines()
        version = version_lines[0] if version_lines else tool
    report = {"status": "partial" if issues else "success", "engine": tool, "version": version,
              "main": rel.as_posix(), "source_sha256": originhash, "converged": stable,
              "commands": records, "engine_attempts": attempts, "diagnostics": issues,
              "pdf": pdf.name if pdf.is_file() else None}
    write(out / "build.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("main")
    parser.add_argument("out", type=Path)
    parser.add_argument("--engine", choices=list(FLAGS))
    args = parser.parse_args()
    result = build(args.project, args.main, args.out, args.engine)
    print(result["status"], result["diagnostics"][:6])
    raise SystemExit(result["status"] != "success")
