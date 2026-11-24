"""Match numerical results to expressly named groups in a parallel passage."""

import re
from collections import Counter


def arm_names(glossary, translated):
    names = {}
    for term, spec in glossary.items():
        if not translated:
            names[term] = [term]
        elif isinstance(spec, str):
            names[term] = [spec]
        else:
            aliases = spec.get("accepted", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            names[term] = [spec.get("target"), *aliases]
    return names


def ordered_arms(text, names, term_spans):
    spans = sorted(
        {
            (a, b, key)
            for key, variants in names.items()
            for variant in variants
            for a, b in term_spans(text, variant)
        }
    )
    if any(end > start for (_, end, _), (start, _, _) in zip(spans, spans[1:])):
        return []
    keys = [key for _, _, key in spans]
    return keys if len(set(keys)) == len(keys) else []


def groups(text, names, term_spans, quantities, split_clauses):
    # Bound 'respectively' to a single sentence or semicolon-delimited assertion.
    assigned = {}
    for sentence in re.split(r"[;；。!?！？]|(?<!\d)\.(?=\s|$)", text):
        if not quantities(sentence):
            continue
        if re.search(r"\brespectively\b|分别|依次", sentence, re.I):
            keys = ordered_arms(sentence, names, term_spans)
            values = quantities(sentence)
            if len(keys) < 2 or len(keys) != len(values):
                continue
            pairs = [(key, [value]) for key, value in zip(keys, values)]
        else:
            pairs = []
            for clause in split_clauses(sentence):
                keys = ordered_arms(clause, names, term_spans)
                values = quantities(clause)
                if len(keys) == 1 and values:
                    pairs.append((keys[0], values))
        for key, values in pairs:
            assigned.setdefault(key, []).extend(values)
    return assigned


def align(original, target, glossary, term_spans, quantities, split_clauses):
    left = groups(
        original, arm_names(glossary, False), term_spans, quantities, split_clauses
    )
    right = groups(
        target, arm_names(glossary, True), term_spans, quantities, split_clauses
    )
    rows = [
        {"entity": key, "original": left[key], "translated": right[key]}
        for key in left
        if key in right
    ]
    complete = (
        len(rows) >= 2
        and set(left) == set(right)
        and Counter(v for values in left.values() for v in values)
        == Counter(quantities(original))
        and Counter(v for values in right.values() for v in values)
        == Counter(quantities(target))
    )
    return rows, complete
