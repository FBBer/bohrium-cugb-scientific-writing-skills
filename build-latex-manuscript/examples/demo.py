"""Self-contained synthetic example; pass a new local output directory."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from casework import atomic_text,prepare,read,write,validate
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()/"demo-output"
inp=out/"input"; work=out/"work"; result=out/"output"
for d in (inp,work,result):d.mkdir(parents=True,exist_ok=True)
case={"case_id":"synthetic-example","output_contract":{"required":["case_id","outcome","status","evidence","uncertainty"]}}
write(inp/"case.json",case)
def setup(files):
    for name,body in files.items():atomic_text(inp/name,body)
    return prepare(inp,work)
def evidence(idx,quote):
    row=next(r for r in idx["sources"] if quote in r["text"])
    return {"id":row["id"],"quote":quote}
def done(outcome,ev,uncertainty=(),status="success"):
    body={"case_id":case["case_id"],"outcome":outcome,"status":status,"evidence":ev,"uncertainty":list(uncertainty)}
    write(result/"result.json",body)
    errors=validate(case,read(result/"result.json"))
    if errors: raise SystemExit(str(errors))
    print("Example result:",result/"result.json")
from build import build
project=inp/"project";project.mkdir(exist_ok=True)
source=r"""\documentclass{article}
\usepackage{amsmath}
\begin{document}
\section{Synthetic calibration}
\begin{equation}\label{eq:gain}g=x_1/x_0.\end{equation}
The gain is defined by Eq.~\eqref{eq:gain}.
\begin{tabular}{lr}Setting & Value\\ A & 4\\\end{tabular}
\end{document}
"""
atomic_text(project/"main.tex",source)
r=build(project,"main.tex",result/"latex-build");assert r["status"]=="success",r["diagnostics"]
assert (result/"latex-build/manuscript.pdf").read_bytes().startswith(b"%PDF-")
assert (result/"latex-build/source/main.tex").read_text()==source
done({"file":"latex-build/manuscript.pdf","source":"latex-build/source/main.tex","converged":r["converged"]},[{"source":"project/main.tex","location":"eq:gain"}])
