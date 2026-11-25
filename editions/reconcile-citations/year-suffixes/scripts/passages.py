"""Locate a literal quotation inside one identified source block, retaining its context."""
import hashlib


def locate(block, ref):
    text, literal = block["text"], ref.get("quote")
    if not isinstance(literal, str) or not literal:
        raise ValueError("a nonempty quotation is required")
    found = []
    at = text.find(literal)
    while at >= 0:
        end = at + len(literal)
        if (("start" not in ref or ref["start"] == at)
                and text[:at].endswith(ref.get("prefix", ""))
                and text[end:].startswith(ref.get("suffix", ""))):
            found.append(at)
        at = text.find(literal, at+1)
    if len(found) != 1:
        raise ValueError("quotation does not identify one occurrence; supply start, prefix or suffix")
    start = found[0]
    end = start + len(literal)
    return {"source":block["source"], "location":block["location"],
            "block_sha256":hashlib.sha256(text.encode()).hexdigest(), "start":start, "end":end,
            "exact":literal, "prefix":text[max(0, start-40):start], "suffix":text[end:end+40]}
