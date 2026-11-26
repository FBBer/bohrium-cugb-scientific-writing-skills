"""Create fictional field notes and a separate example plan illustrating the writing input."""
import argparse
import json
from pathlib import Path

def make(root,plan_file):
    root.mkdir(parents=True,exist_ok=True)
    if any((root/f).exists() for f in ("flume.md","bank.md","crossing.md","task.md","case.json")) or plan_file.exists():
        raise FileExistsError("choose unused sample paths")
    a="Depth readings at an exposed bank varied with the tide."
    b="Depth was measured only at an exposed bank."
    d="Depth was measured only in a sheltered flume."
    e="We recorded depth at both banks during the same tide."
    (root/"bank.md").write_text("Bank transect field note\n\n"+a+"\n\n"+b+"\n")
    (root/"flume.md").write_text("Flume field note\n\n"+d+"\n")
    (root/"crossing.md").write_text(e+"\n")
    def ref(f,q):return {"file":f,"quote":q}
    both=[ref("bank.md",b),ref("flume.md",d)]
    plan={"language":"en","title":"Depth across a tidal channel","own":["crossing.md"],
          "works":{"bank.md":"Bank transect field note","flume.md":"Flume field note"},
          "paragraphs":[
            {"role":"background","claims":[{"text":"Water depth at the exposed bank varied with the tide.","evidence":[ref("bank.md",a)]}]},
            {"role":"comparison","claims":[{"text":"The two depth measurements describe different settings.","evidence":both,
             "comparison":{"kind":"contrast","by_source":{"bank.md":{"metric":"Depth","condition":"exposed bank"},"flume.md":{"metric":"Depth","condition":"sheltered flume"}}}}]},
            {"role":"gap","claims":[{"text":"Within these two surveys, neither measurement spans both settings.","evidence":both,
             "gap":{"kind":"limitation","scope":"these two surveys","papers":["bank.md","flume.md"]}}]},
            {"role":"contribution","claims":[{"text":"We recorded depth at both banks during the same tide.","evidence":[ref("crossing.md",e)]}]}
          ]}
    (root/"task.md").write_text("Write an introduction comparing the channel observations with a flume study. Name the sampling gap and state the field contribution.")
    (root/"case.json").write_text(json.dumps({"case_id":"sample-channel","output_contract":{"required_fields":["case_id","manuscript","evidence","status"]}}))
    plan_file.parent.mkdir(parents=True,exist_ok=True)
    plan_file.write_text(json.dumps(plan,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("input",type=Path);p.add_argument("plan",type=Path)
    a=p.parse_args();make(a.input,a.plan)
