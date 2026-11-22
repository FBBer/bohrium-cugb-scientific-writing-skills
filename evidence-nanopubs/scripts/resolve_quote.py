"""Read evidence from a TriG nanopublication and recover the quotation from its source index."""

import argparse
import hashlib
from pathlib import Path

from casework import read


def resolve(trig, source_index, nanopub=None):
    from rdflib import Dataset, Namespace, RDF, URIRef
    from rdflib.namespace import DCTERMS, PROV

    oa = Namespace("http://www.w3.org/ns/oa#")
    np = Namespace("http://www.nanopub.org/nschema#")
    fields = Namespace("urn:scholar:field:")
    ds = Dataset()
    ds.parse(trig, format="trig")
    ds.default_union = True
    sources = {}
    for block in source_index["sources"]:
        key = (
            block["source"],
            block["location"],
            hashlib.sha256(block["text"].encode()).hexdigest(),
        )
        sources[key] = block["text"]
    rows = []
    wanted = URIRef(nanopub) if nanopub else None
    for publication, _, provenance in ds.triples((wanted, np.hasProvenance, None)):
        graph = ds.graph(provenance)
        assertion = ds.value(publication, np.hasAssertion)
        for evidence in graph.objects(assertion, PROV.wasDerivedFrom):
            block = graph.value(evidence, oa.hasSource)
            if block is None:
                raise ValueError("evidence has no source-block selector")
            document = graph.value(block, DCTERMS.isPartOf)
            location = str(graph.value(block, DCTERMS.identifier))
            checksum = str(graph.value(block, fields.blockSha256))
            names = [str(v) for v in graph.objects(document, DCTERMS.identifier)]
            matches = [
                (name, sources[(name, location, checksum)])
                for name in names
                if (name, location, checksum) in sources
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"{location}: supply the cited document edition and source block"
                )
            name, text = matches[0]
            selectors = {
                graph.value(s, RDF.type): s
                for s in graph.objects(evidence, oa.hasSelector)
            }
            if (
                oa.TextPositionSelector not in selectors
                or oa.TextQuoteSelector not in selectors
            ):
                raise ValueError(f"{location}: missing position or quotation selector")
            pos, quote = (
                selectors[oa.TextPositionSelector],
                selectors[oa.TextQuoteSelector],
            )
            start, end = int(graph.value(pos, oa.start)), int(graph.value(pos, oa.end))
            exact = str(graph.value(quote, oa.exact))
            prefix, suffix = (
                str(graph.value(quote, term) or "") for term in (oa.prefix, oa.suffix)
            )
            if not (
                0 <= start < end <= len(text)
                and text[start:end] == exact
                and text[:start].endswith(prefix)
                and text[end:].startswith(suffix)
            ):
                raise ValueError(
                    f"{name} {location}: selectors disagree with the source"
                )
            rows.append(
                {
                    "publication": str(publication),
                    "source": name,
                    "location": location,
                    "start": start,
                    "end": end,
                    "quote": exact,
                    "prefix": prefix,
                    "suffix": suffix,
                }
            )
    if not rows:
        raise ValueError("the requested nanopublication has no matching evidence")
    return sorted(
        rows, key=lambda r: (r["publication"], r["source"], r["location"], r["start"])
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trig", type=Path)
    parser.add_argument("index", type=Path)
    parser.add_argument("--publication", help="Full nanopublication IRI")
    args = parser.parse_args()
    try:
        for row in resolve(args.trig, read(args.index), args.publication):
            print(
                f"{row['source']} · {row['location']} · [{row['start']},{row['end']})"
            )
            print(f"{row['prefix']}【{row['quote']}】{row['suffix']}")
    except (ValueError, ImportError) as exc:
        parser.exit(1, f"{exc}\n")
