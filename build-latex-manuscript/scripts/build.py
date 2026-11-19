"""Stage an editable TeX project, compile to convergence, retain diagnostics and a fresh PDF."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from casework import write,atomic_text

GENERATED={".aux",".log",".out",".toc",".bcf",".blg",".lof",".lot",".fls",".fdb_latexmk",".synctex.gz",".run.xml",".nav",".snm",".xdv"}
DIAGNOSTIC=re.compile(r"^! |:[0-9]+: |undefined (?:references|citations)|(?:Citation|Reference) .+ undefined|multiply.defined|Overfull \\[hv]box|Missing character:|Rerun to get|Please \(re\)run|^LaTeX Error|Emergency stop",re.I)

def engine_for(path):
    t=path.read_text(encoding="utf-8",errors="replace")
    directive=re.search(r"(?im)^%\s*!\s*TEX\s+program\s*=\s*(pdf|xe|lua)latex\b",t)
    if directive:return directive[1].lower()+"latex"
    if re.search(r"\\(?:usepackage|RequirePackage|documentclass)(?:\[[^\]]*\])?\{[^}]*?(?:fontspec|xeCJK|ctex|unicode-math)",t) or re.search("[\u3400-\u9fff]",t):return "xelatex"
    return "pdflatex"


def invoke(argv,cwd,records,env):
    try:
        p=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=125,check=False)
        output=p.stdout.decode("utf-8",errors="replace");rc=p.returncode
    except (OSError,subprocess.TimeoutExpired) as err:output=str(err);rc=124
    records.append({"argv":argv,"exit":rc,"tail":output.splitlines()[-20:]});return rc,output


def build(project,main,out,engine=None):
    project=project.resolve();out=out.resolve();rel=Path(main)
    if rel.is_absolute() or ".." in rel.parts or not (project/rel).is_file():raise ValueError("main must be a file inside the source project")
    if project==out or project in out.parents:raise ValueError("output directory must be outside the source tree")
    out.mkdir(parents=True,exist_ok=True)
    source=out/"source";records=[];issues=[];pdf=out/"manuscript.pdf"
    if pdf.exists():pdf.unlink()
    if source.exists():
        # Only replace files in the generated source copy. Avoid recursive removal of an unrelated directory.
        if not (out/".build-output").is_file():raise ValueError("use a fresh output directory")
        shutil.rmtree(source)
    atomic_text(out/".build-output","build-latex-manuscript\n")
    originhash={}
    for path in sorted(project.rglob("*")):
        relative=path.relative_to(project)
        if not path.is_file() or any(p.startswith(".") for p in relative.parts) or path.is_symlink():continue
        if any(str(path).endswith(s) for s in GENERATED) or relative==rel.with_suffix(".pdf"):continue
        dest=source/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        originhash[relative.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    tool=engine or engine_for(source/rel);env=os.environ.copy()
    if tool not in {"pdflatex","xelatex","lualatex"}:raise ValueError("unknown engine")
    version=shutil.which(tool)
    if version:
        v=subprocess.run([tool,"--version"],capture_output=True,text=True).stdout.splitlines();version=v[0] if v else tool
    stable=False;status="partial";stem=rel.stem
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)/"project";shutil.copytree(source,stage)
        cwd=stage
        env.update({"openout_any":"p","openin_any":"p","shell_escape":"f"})
        logfile=cwd/(stem+".log");built=cwd/(stem+".pdf")
        if shutil.which("latexmk") and shutil.which(tool):
            flag={"pdflatex":"-pdf","xelatex":"-xelatex","lualatex":"-lualatex"}[tool]
            cmds=["latexmk","-norc",flag,"-no-shell-escape","-interaction=nonstopmode","-halt-on-error","-file-line-error",rel.as_posix()]
            rc,output=invoke(cmds,cwd,records,env);stable=(rc==0)
        elif shutil.which(tool):
            before=None;bibsig=None;rc=1
            for iteration in range(6):
                rc,output=invoke([tool,"-no-shell-escape","-interaction=nonstopmode","-halt-on-error","-file-line-error",rel.as_posix()],cwd,records,env)
                if rc:break
                aux=cwd/(stem+".aux");bcf=cwd/(stem+".bcf")
                auxtext=aux.read_text(errors="replace") if aux.exists() else ""
                bibfile=bcf if bcf.exists() else aux if "\\bibdata" in auxtext else None
                bibtool="biber" if bcf.exists() else "bibtex"
                if bibfile:
                    bibkey=bcf.read_bytes() if bcf.exists() else "\n".join(l for l in auxtext.splitlines() if l.startswith(("\\citation","\\bibdata","\\bibstyle"))).encode()
                    if bibkey!=bibsig:
                        rc,output=invoke([bibtool,stem],cwd,records,env);bibsig=bibkey
                        if rc:break
                        before=None;continue
                now={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cwd.rglob("*") if p.is_file() and p.suffix in {".aux",".toc",".bbl",".out",".lof",".lot"}}
                if before==now:stable=True;break
                before=now
        else:
            rc=127;output=tool+" not installed"
        log=logfile.read_text(errors="replace") if logfile.exists() else output
        atomic_text(out/"compile.log",log)
        issues=[s.strip() for s in log.splitlines() if DIAGNOSTIC.search(s)]
        for row in records:
            if row["exit"]:issues.extend(row["tail"][-5:])
        if rc:issues.append("compiler exited "+str(rc))
        if not stable:issues.append("convergence not established")
        if built.is_file() and built.read_bytes()[:5]==b"%PDF-" and rc==0:
            shutil.copy2(built,pdf)
            if not issues and stable:status="success"
        else:issues.append("no successful fresh PDF")
    report={"status":status,"engine":tool,"version":version,"main":rel.as_posix(),"source_sha256":originhash,"converged":stable,"commands":records,"diagnostics":issues,"pdf":pdf.name if pdf.is_file() else None}
    write(out/"build.json",report);return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("project",type=Path);p.add_argument("main");p.add_argument("out",type=Path);p.add_argument("--engine",choices=["pdflatex","lualatex","xelatex"])
    a=p.parse_args();r=build(a.project,a.main,a.out,a.engine);print(r["status"],r["diagnostics"][:6]);raise SystemExit(r["status"]!="success")
