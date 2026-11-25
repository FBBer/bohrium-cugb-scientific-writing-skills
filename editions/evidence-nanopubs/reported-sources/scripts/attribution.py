from pathlib import Path
import argparse
import json
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("materials", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
root = args.materials.resolve()
out = args.destination.resolve()
out.mkdir(parents=True, exist_ok=True)

def output(name, value):
    (out / name).write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

import hashlib
from urllib.parse import quote

def iri(value):
    return "<urn:source:" + quote(str(value), safe="") + ">"

def literal(value):
    return json.dumps(str(value), ensure_ascii=False)

claims = json.loads((root / "claims.json").read_text())
graphs = ["@prefix np: <http://www.nanopub.org/nschema#> .", "@prefix prov: <http://www.w3.org/ns/prov#> .", "@prefix ex: <urn:ground:> ."]
records = []
for row in claims:
    page = (root / row["file"]).resolve()
    if root not in page.parents:
        raise ValueError("Source outside materials")
    lines = page.read_text().splitlines()
    number = int(row["line"])
    if not 1 <= number <= len(lines) or row["quote"] not in lines[number-1] or not row["quote"].strip():
        raise ValueError("Missing quotation at " + row["file"] + ":" + str(number))
    kind = row["kind"]
    if kind not in ("measured", "reported") or (kind == "reported" and not row.get("cited")):
        raise ValueError("A reported result requires an identified cited work")
    reference = row.get("cited") if kind == "reported" else row["file"]
    key = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:22]
    base = "urn:np:" + key
    n,h,a,p,i = ["<" + base + suffix + ">" for suffix in ("", "#head","#assertion","#provenance","#pubinfo")]
    relationship = "ex:reports" if kind == "reported" else "ex:observes"
    graphs.extend([f"{h} {{ {n} a np:Nanopublication ; np:hasAssertion {a} ; np:hasProvenance {p} ; np:hasPublicationInfo {i} . }}",
                   f"{a} {{ {iri(row['file'])} {relationship} {literal(row['quote'])} . }}",
                   f"{p} {{ {a} prov:wasDerivedFrom {iri(row['file']+'#L'+str(number))} ; ex:attributedWork {iri(reference)} . }}",
                   f"{i} {{ {n} prov:wasAttributedTo <urn:agent:GPT-6.2Astra> . }}"])
    records.append({"nanopublication":base,"evidence_type":kind,"source":row["file"],"line":number,"attributed_work":reference,"quotation":row["quote"]})
output("assertions.trig", "\n".join(graphs)+"\n")
output("provenance.json",records)
