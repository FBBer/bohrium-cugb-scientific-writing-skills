"""Assemble the requested case fields from actual artifacts, then replace the result atomically."""
from pathlib import Path
import re

from casework import read, validate, write


def parts(pointer):
    if pointer == "":
        return []
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError(f"Invalid JSON pointer: {pointer!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def child(node, key):
    if isinstance(node, list) and re.fullmatch(r"0|[1-9][0-9]*", key):
        return node[int(key)]
    if isinstance(node, dict):
        return node[key]
    raise ValueError(f"Cannot resolve {key!r} in this value")


def insert(document, pointer, value):
    path = parts(pointer)
    if not path or path[0] == "case_id":
        raise ValueError("Bind a named result field; case_id is read from the case")
    target = document
    for key in path[:-1]:
        if isinstance(target, dict):
            target = target.setdefault(key, {})
        else:
            target = child(target, key)
    key = path[-1]
    if not isinstance(target, dict) or key in target:
        raise ValueError(f"Supply {pointer} once as an object field; arrays can be read from JSON")
    target[key] = value


def assemble(case_path, result_path, fields, json_files, text_files, linked_files):
    case = read(case_path)
    result = Path(result_path).resolve()
    document = read(fields) if fields else {}
    if not isinstance(document, dict):
        raise ValueError("The fields file must contain a JSON object")
    if "case_id" not in case:
        raise ValueError("The input has no case_id")
    if document.setdefault("case_id", case["case_id"]) != case["case_id"]:
        raise ValueError("The supplied case_id differs from the input case")

    def artifact(filename):
        relative = Path(filename)
        source = (result.parent / relative).resolve()
        if relative.is_absolute() or source == result or result.parent not in source.parents:
            raise ValueError(f"Use an existing artifact inside the output folder: {filename}")
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing or empty output artifact: {filename}")
        return source

    for dest, filename, pointer in json_files:
        value = read(artifact(filename))
        for key in parts(pointer):
            value = child(value, key)
        insert(document, dest, value)
    for dest, filename in text_files:
        insert(document, dest, artifact(filename).read_text(encoding="utf-8-sig"))
    for dest, filename in linked_files:
        insert(document, dest, artifact(filename).relative_to(result.parent).as_posix())
    errors = validate(case, document)
    if errors:
        raise ValueError("\n".join(errors))
    write(result, document)
    return result
