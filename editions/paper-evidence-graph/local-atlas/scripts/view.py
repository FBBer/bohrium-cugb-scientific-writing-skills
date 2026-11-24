"""Read query diagrams and their original evidence without a network connection."""
from pathlib import Path
from reader import bitmap, cli, data, details, esc, paragraph, section, table
TITLE = "文献知识图谱"

def body(source):
    graph = data(source)
    nodes = {n["id"]:n["label"] for n in graph["nodes"]}
    edges = {e["id"]:e for e in graph["edges"]}
    answers_file = source.with_name("queries.json")
    answers = data(answers_file) if answers_file.is_file() else []
    figures = source.parent/"figures"
    parts = []
    for i, query in enumerate(answers, 1):
        images = []
        for file in sorted(figures.glob(f"query-{i:02d}-*.svg")) if query.get("edges") else ():
            images.append('<div class="drawing">' + bitmap(file.read_bytes(),"image/svg+xml",query["question"]) + '</div>')
        rows, quotes = [], []
        for key in query.get("edges", []):
            e = edges[key]
            rows.append([nodes[e["source"]],e.get("display_predicate") or e["predicate"],nodes[e["target"]],e["scope"]])
            for a in e.get("evidence", []):
                ref = graph.get("anchors", {}).get(a["id"], {})
                loc = " · ".join(filter(None, (ref.get("source"),ref.get("location"))))
                quotes.append(paragraph(a["quote"]) + paragraph(loc))
        if images:
            content = "".join(images)
        elif rows:
            content = section(query["question"],table(("主体","关系","客体","条件"),rows))
        else:
            content = section(query["question"],paragraph("已有材料没有给出符合此查询的关系。"))
        if quotes:
            content += details("查看原句", "".join(dict.fromkeys(quotes)))
        parts.append('<article>' + content + '</article>')
    if not parts:
        rows = [[nodes[e["source"]],e.get("display_predicate") or e["predicate"],nodes[e["target"]],e["scope"]] for e in edges.values()]
        parts.append(table(("主体","关系","客体","条件"),rows) or paragraph("材料中没有可绘制的关系。"))
    return "".join(parts)

if __name__ == "__main__":
    cli(TITLE, body)
