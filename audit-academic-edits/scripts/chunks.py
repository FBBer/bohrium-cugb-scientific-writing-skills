"""Prepare overlapping reading context and reunite disjoint edits in manuscript order."""
import argparse
import hashlib
import json
from pathlib import Path

from casework import read, write


def fingerprint(source):
    payload = json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def partition(source, limit, overlap):
    rows = source["segments"]
    ids = [r["id"] for r in rows]
    if not rows or len(set(ids)) != len(ids) or limit < 1 or overlap < 0:
        raise ValueError("use a nonempty source with distinct segment IDs, a positive size and nonnegative context")
    groups = []
    left = 0
    while left < len(rows):
        right = left
        length = 0
        while right < len(rows):
            size = len(rows[right]["text"])
            if right > left and length + size > limit:
                break
            length += size
            right += 1
        groups.append({"before":rows[max(0, left-overlap):left], "edit":rows[left:right],
                       "after":rows[right:right+overlap]})
        left = right
    return groups


def prepare(source, folder, limit, overlap):
    groups = partition(source, limit, overlap)
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("choose an empty packet folder so an existing translation is preserved")
    signature = fingerprint(source)
    names = []
    for number, group in enumerate(groups, 1):
        name = f"part-{number:03d}.json"
        names.append(name)
        write(folder/name, {"manuscript":signature, "part":number, **group,
                            "draft":[{"id":r["id"], "target":""} for r in group["edit"]]})
    write(folder/"manifest.json", {"manuscript":signature, "parts":names,
                                   "segment_ids":[[r["id"] for r in group["edit"]] for group in groups]})
    return len(groups)


def assemble(source, folder):
    manifest = read(folder/"manifest.json")
    originals = {r["id"]:r for r in source["segments"]}
    ids = [r["id"] for r in source["segments"]]
    groups = manifest["segment_ids"]
    if (manifest["manuscript"] != fingerprint(source) or len(groups) != len(manifest["parts"])
            or [key for group in groups for key in group] != ids or len(set(ids)) != len(ids)):
        raise ValueError("the packet set belongs to a different manuscript or segment order")
    result = []
    for number, (name, keys) in enumerate(zip(manifest["parts"], groups), 1):
        if name != f"part-{number:03d}.json":
            raise ValueError("unexpected packet filename")
        part = read(folder / name)
        if (part["part"] != number or part["manuscript"] != manifest["manuscript"]
                or part["edit"] != [originals[key] for key in keys]):
            raise ValueError(f"{name} does not match its original section")
        items = part["draft"]
        by_id = {r["id"]:r for r in items}
        if len(by_id) != len(items) or set(by_id) != set(keys):
            raise ValueError(f"{name} has missing, repeated or out-of-scope segment IDs")
        for key in keys:
            entry = by_id[key]
            if not isinstance(entry.get("target"), str) or not entry["target"].strip():
                raise ValueError(f"{name} needs text for {key}")
            result.append(entry)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split")
    split.add_argument("--chars", type=int, default=5000)
    split.add_argument("--context", type=int, default=1)
    merge = sub.add_parser("merge")
    for cmd in (split, merge):
        cmd.add_argument("source", type=Path)
        cmd.add_argument("packets", type=Path)
    merge.add_argument("out", type=Path)
    args = parser.parse_args()
    try:
        source = read(args.source)
        if args.command == "split":
            print(prepare(source, args.packets, args.chars, args.context), "packets")
        else:
            draft = assemble(source, args.packets)
            write(args.out, draft)
            print(len(draft), "segments")
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
