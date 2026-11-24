"""Keep a named supplementary table with its paper and look up a reported cell."""

import csv
from pathlib import Path


def collect_tables(folder, selected, links, index):
    available = {f["path"] for f in index["files"]}
    result = {}
    for declaration in links:
        paper, sep, table = declaration.partition("=")
        if (
            not sep
            or paper not in selected
            or table not in available
            or Path(table).suffix.lower() not in {".csv", ".tsv"}
        ):
            raise ValueError("Use --table 'selected-paper=relative-table.csv' or .tsv")
        if table in result and result[table]["paper"] != paper:
            raise ValueError("A supplementary table must identify one paper")
        if table in result:
            continue
        with (folder / table).open(encoding="utf-8-sig", newline="") as stream:
            rows = csv.reader(
                stream,
                delimiter="\t" if table.lower().endswith(".tsv") else ",",
                strict=True,
            )
            headers = None
            records = []
            for r, values in enumerate(rows, 1):
                if not any(v.strip() for v in values):
                    continue
                if headers is None:
                    headers = [v.strip() for v in values]
                    headrow = r
                    if any(not v for v in headers) or len(set(headers)) != len(headers):
                        raise ValueError(
                            f"{table}: headers must be nonempty and unique"
                        )
                else:
                    if len(values) > len(headers):
                        raise ValueError(f"{table}: row {r} exceeds its header")
                    records.append({"row": r, "values": values})
        if not headers:
            raise ValueError(f"Empty table: {table}")
        result[table] = {
            "paper": paper,
            "source": table,
            "header_row": headrow,
            "headers": headers,
            "rows": records,
        }
    return result


def lookup(table, where, field):
    headers = table["headers"]
    for key in [field, *where]:
        if key not in headers:
            raise ValueError(f"Unknown table field: {key}")
    found = []
    col = headers.index(field)
    for r in table["rows"]:
        values = r["values"]
        if not all(
            headers.index(k) < len(values) and values[headers.index(k)] == v
            for k, v in where.items()
        ):
            continue
        value = values[col] if col < len(values) else None
        found.append(
            {
                "location": f"R{r['row']}:C{col + 1}",
                "value": value,
                "fields": dict(zip(headers, values)),
                "state": "absent_cell"
                if value is None
                else "blank"
                if not value.strip()
                else "reported",
            }
        )
    return {
        "paper": table["paper"],
        "source": table["source"],
        "field": field,
        "header_location": f"R{table['header_row']}:C{col + 1}",
        "where": where,
        "state": "no_match"
        if not found
        else "ambiguous"
        if len(found) > 1
        else found[0]["state"],
        "matches": found,
    }
