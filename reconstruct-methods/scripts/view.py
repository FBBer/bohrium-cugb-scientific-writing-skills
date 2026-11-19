"""Present the methods and the settings used for the reported run."""
from reader import cli, data, details, esc, manuscript, paragraph, section, table
TITLE = "方法与实验"

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
        names = {"seed":"随机种子","updates":"更新次数","rate":"速率参数","split":"数据划分","random_seed":"随机种子","effective_run":"实验记录"}
        fields = [(names.get(k,k),v) for k,v in record.items() if isinstance(v,(str,float,int))]
        if fields:
            content += details("运行设置", table(("设置","记录值"), fields))
    return content

if __name__ == "__main__":
    cli(TITLE, body)
