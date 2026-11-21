"""Look up an observation within one source record and retain its original field locations."""
import csv
import json


def pointer_key(key):
    return str(key).replace("~", "~0").replace("/", "~1")


def scalar(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def json_records(data, source, append, root=""):
    identifiers = {"id", "paper_id", "study_id", "document_id", "source_id", "run_id", "sample_id", "title",
                   "section", "year", "doi", "name", "group", "sample", "condition", "study", "dataset"}

    def walk(value, location, parents):
        if isinstance(value, list):
            for i, child in enumerate(value):
                yield from walk(child, f"{location}/{i}", parents)
            return
        if not isinstance(value, dict):
            if value is not None:
                append(source, location or "/", scalar(value))
            return
        fields = []
        for key, child in value.items():
            if child is None or isinstance(child, (dict, list)):
                continue
            anchor = append(source, location + "/" + pointer_key(key), scalar(child))
            if anchor:
                fields.append({"field": str(key), "id": anchor})
        if fields:
            yield {"source": source, "location": location or "/", "fields": fields, "parents": parents}
        inherited = {f["field"]: f for f in parents}
        inherited.update({f["field"]: f for f in fields if f["field"].casefold() in identifiers})
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                yield from walk(child, location + "/" + pointer_key(key), list(inherited.values()))
    yield from walk(data, root, [])


def delimited_records(path, source, append):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t" if path.suffix.lower() == ".tsv" else ",", strict=True)
        headers = None
        physical = 0
        for number, values in enumerate(reader, 1):
            start, physical = physical + 1, reader.line_num
            if not any(value.strip() for value in values):
                continue
            position = "R" + str(number)
            cells = [(i, value, append(source, position + ":C" + str(i), value))
                     for i, value in enumerate(values, 1)]
            if headers is None:
                headers = {i: (value, anchor) for i, value, anchor in cells}
                continue
            fields = []
            for i, _, anchor in cells:
                if not anchor:
                    continue
                label, head = headers.get(i, ("", None))
                fields.append({"field": label or f"#{i}", "column": i, "id": anchor, "header": head})
            yield {"source": source, "location": position, "lines": [start, physical], "fields": fields}


def lookup(index, source, criteria, selected, limit):
    if limit < 1:
        raise ValueError("limit must be positive")
    sources = {r["id"]: r for r in index["sources"]}
    if source not in {f["path"] for f in index["files"]}:
        raise ValueError("source is absent from this index: " + source)

    def evidence(field):
        item = sources[field["id"]]
        result = {"field": field["field"], "id": item["id"], "location": item["location"], "quote": item["text"]}
        if field.get("header"):
            h = sources[field["header"]]
            result["header"] = {"id": h["id"], "location": h["location"], "quote": h["text"]}
        return result

    def names(field, name):
        return field["field"] == name or ("column" in field and name == "#" + str(field["column"]))

    matches, total = [], 0
    for record in index.get("records", []):
        if record["source"] != source:
            continue
        fields = record["fields"]
        local = {f["field"] for f in fields}
        context = [f for f in record.get("parents", []) if f["field"] not in local]
        available = fields + context
        if not all(any(names(f, key) and sources[f["id"]]["text"] == value for f in available)
                   for key, value in criteria):
            continue
        values = [f for f in fields if not selected or any(names(f, key) for key in selected)]
        if not values:
            continue
        total += 1
        if len(matches) < limit:
            keys = [f for f in available if any(names(f, k) and sources[f["id"]]["text"] == v for k, v in criteria)]
            hit = {"location": record["location"], "matched_fields": [evidence(f) for f in keys],
                   "values": [evidence(f) for f in values]}
            if "lines" in record:
                hit["lines"] = record["lines"]
            matches.append(hit)
    return {"case_id": index.get("case_id"), "source": source, "total": total, "matches": matches}
