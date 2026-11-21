"""Collect source-located settings and compare reported values within compatible runs and stages."""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path
import re

from casework import write


SCOPE_KEYS = {"run_id": "run", "trial_id": "trial", "experiment_id": "experiment",
              "stage": "stage", "phase": "stage", "split": "split"}
ASSIGNMENT = re.compile(r"""(?<![\w-])([A-Za-z_][\w.-]*)\s*[:=]\s*("[^"]*"|'[^']*'|[-+.\w/%]+)""")
UNIT = re.compile(r"[ \t]*(ms|µs|μs|ns|s|Hz|kHz|MHz|mV|V|mA|A|Pa|kPa|MPa|mm|cm|m|mg|kg|g|°C|%)(?![\w:=])")


def scope_of(record, parent=None):
    scope = dict(parent or {})
    local = {SCOPE_KEYS[k.casefold()]: str(v).strip() for k, v in record.items()
             if isinstance(k, str) and k.casefold() in SCOPE_KEYS and v not in (None, "") and isinstance(v, (str, int, float))}
    if any(k in local and local[k] != scope.get(k) for k in ("run", "trial", "experiment")):
        scope = {k: v for k, v in scope.items() if k not in ("stage", "split")}
    return {**scope, **local}


def structured(node, location="", name="", scope=None):
    if isinstance(node, dict):
        scope = scope_of(node, scope)
        if "value" in node and isinstance(node.get("name") or name, str) and (node.get("name") or name) and not isinstance(node["value"], (dict, list)):
            yield node.get("name") or name, node["value"], node.get("unit"), location + "/value", scope
            return
        for key, value in node.items():
            key = str(key)
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from structured(value, location + "/" + escaped, key, scope)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from structured(value, location + "/" + str(i), name, scope)
    elif node is not None and name:
        yield name, node, None, location, scope


def distinct_value(value):
    try:
        number = Decimal(value)
        return number if number.is_finite() else value
    except (ValueError, InvalidOperation):
        return value


def conflicts(rows):
    # Compare distinct reported settings, not every pair of repeated log samples.
    groups = defaultdict(list)
    for row in rows:
        key = (tuple(sorted(row["scope"].items())), distinct_value(row["value"]), row["unit"])
        groups[key].append(row)
    keys = list(groups)
    involved = set()
    for i, (left, value, unit) in enumerate(keys):
        left = dict(left)
        for j in range(i + 1, len(keys)):
            right, other_value, other_unit = keys[j]
            if value == other_value and (unit == other_unit or not unit or not other_unit):
                continue
            if all(k not in left or left[k] == v for k, v in right):
                involved.update((i, j))
    return [row for i in sorted(involved) for row in groups[keys[i]]]


def collect(root):
    observations = defaultdict(list)
    issues = []

    def add(name, value, unit, location, scope):
        if not name or value is None or value == "":
            return
        observations[name.casefold()].append({"name": name, "value": str(value), "unit": unit or None,
                                              "file": rel, "locator": location, "scope": scope or {}})

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in {"case.json", "task.md"}:
            continue
        ext = path.suffix.lower()
        rel = path.relative_to(root).as_posix()
        if ext not in {".json", ".yml", ".yaml", ".csv", ".tsv", ".txt", ".log", ".cfg", ".ini", ".toml"}:
            continue
        try:
            raw = path.read_text(encoding="utf-8-sig")
            data = None
            if ext == ".json":
                data = json.loads(raw)
            elif ext in {".yml", ".yaml"}:
                try:
                    import yaml
                except ImportError:
                    pass
                else:
                    try:
                        data = yaml.safe_load(raw)
                    except yaml.YAMLError as error:
                        issues.append({"file": rel, "reason": str(error)})
                        continue
            if data is not None:
                for entry in structured(data):
                    add(*entry)
            elif ext in {".csv", ".tsv"}:
                for i, row in enumerate(csv.DictReader(io.StringIO(raw), delimiter="\t" if ext == ".tsv" else ","), 2):
                    loc = "row " + str(i)
                    scope = scope_of(row)
                    if row.get("name") and "value" in row:
                        add(row["name"], row["value"], row.get("unit"), loc, scope)
                    else:
                        for k, v in row.items():
                            if k and k.casefold() != "unit":
                                add(k, v, None, loc, scope)
            else:
                scope = {}
                for i, line in enumerate(raw.splitlines(), 1):
                    matches = list(ASSIGNMENT.finditer(line))
                    scope = scope_of({m[1]: m[2].strip("\"'") for m in matches}, scope)
                    for m in matches:
                        value = m[2].strip("\"'")
                        unit = UNIT.match(line, m.end()) if re.fullmatch(r"[+-]?[\d.]+(?:[Ee][+-]?\d+)?",value) else None
                        add(m[1], value, unit[1] if unit else None, "L" + str(i), scope)
        except (OSError, ValueError) as error:
            issues.append({"file": rel, "reason": str(error)})
    candidates = {}
    for name, rows in observations.items():
        if name in SCOPE_KEYS:
            continue
        flagged = conflicts(rows)
        if flagged:
            candidates[name] = flagged
    return {"observations": dict(observations), "candidate_conflicts": candidates, "issues": issues}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("materials", type=Path)
    parser.add_argument("out")
    args = parser.parse_args()
    write(args.out, collect(args.materials))
