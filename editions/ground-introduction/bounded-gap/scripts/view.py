"""Read the introduction with its underlying literature comparison."""
from reader import cli, data, details, manuscript, section, table
TITLE = "引言与相关工作"

def body(source):
    content = manuscript(source.read_text(encoding="utf-8"))
    matrix = source.with_name("comparison-matrix.json")
    if not matrix.is_file():
        return content
    rows = data(matrix)
    fields = (("work","研究"),("axis","比较维度"),("method","方法"),("condition","条件"),("observed_result","结果"),("limit","适用范围"))
    columns = [(key, name) for key, name in fields if any(x.get(key) for x in rows)]
    grid = table([name for _, name in columns], ([r.get(key) for key, _ in columns] for r in rows))
    return content + details("逐篇比较", grid)

if __name__ == "__main__":
    cli(TITLE, body)
