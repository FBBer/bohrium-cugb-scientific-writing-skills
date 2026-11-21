"""Present the methods and the settings used for the reported run."""
import csv
from reader import cli, data, details, esc, manuscript, paragraph, section, table
TITLE = "方法与实验"

def disputed_values(source):
    audit = source.with_name("audit.json")
    if not audit.is_file():
        return ""
    report = data(audit)
    passages = {r.get("claim"):r.get("candidate") for r in report.get("unresolved",[]) if r.get("candidate")}
    refs = {}
    manifest = source.with_name("claim-sources.tsv")
    if manifest.is_file():
        with manifest.open(encoding="utf-8",newline="") as handle:
            for row in csv.DictReader(handle,delimiter="\t"):
                refs.setdefault(row["claim"],[]).append(row)
    output = []
    for issue in report.get("issues",[]):
        a,b = issue.get("written_groups"),issue.get("source_groups")
        if not a or not b:
            continue
        claim = issue.get("claim")
        original = passages.get(claim) or str(issue.get("parameter",""))+" · "+"、".join(a)
        number = str(issue.get("measurement",""))
        source_note = "、".join(b)+" · "+number
        positions = issue.get("source_locations",[])
        location = "、".join(r["source"]+" "+r["location"] for r in positions)
        if not location:
            location = next((r["source"]+" "+r["location"] for r in refs.get(claim,[]) if r["quote"]==number),"")
        if issue.get("parameter"):
            params=source.with_name("parameters.json")
            if params.exists():
                row=next((r for r in data(params) if r.get("name")==issue["parameter"] and r.get("scope") in a),{})
                if row.get("unit"):
                    source_note+=" "+row["unit"]
        item=(original,source_note,location)
        if item not in output:
            output.append(item)
    return section("有争议的读数",table(("原稿写法","原始记录","数据位置"),output)) if output else ""


def body(source):
    content = manuscript(source.read_text(encoding="utf-8"))
    parameters = source.with_name("parameters.json")
    if parameters.is_file():
        params = data(parameters)
        rows = [(r.get("name"),r.get("scope"),r.get("value"),
                 "未注明" if r.get("unit_status")=="unreported" and not r.get("unit") else r.get("unit"),
                 r.get("resolution") or r.get("reason")) for r in params]
        if any(r[-1] for r in rows):
            content += section("实验参数", table(("参数","适用条件","取值","单位","取值依据"), rows, numeric=(2,)))
        else:
            content += section("实验参数", table(("参数","适用条件","取值","单位"), (r[:-1] for r in rows), numeric=(2,)))
    reproduction = source.with_name("reproduction.json")
    if reproduction.is_file():
        record = data(reproduction)
        names = {"seed":"随机种子","updates":"更新次数","rate":"速率参数","split":"数据划分","random_seed":"随机种子","effective_run":"实验记录","steps":"复现步骤","missing":"缺失记录","gaps":"缺失记录","artifacts":"材料","limitations":"适用范围"}
        fields = []
        for key,value in record.items():
            if isinstance(value,(str,float,int)):
                fields.append((names.get(key,key),str(value)))
            elif isinstance(value,list) and all(isinstance(v,(str,float,int)) for v in value):
                fields.extend((names.get(key,key),str(v)) for v in value)
        if fields:
            content += details("运行设置", table(("设置","记录值"), fields))
    return content + disputed_values(source)

if __name__ == "__main__":
    cli(TITLE, body)
