# 参考文献与引用管理

重排过的论文正文，加上原始参考文献库。按首次引用顺序重排编号、合并重复记录，保留公式里的下标。

## 试用示例

三条虚构书目含一个重复 DOI，正文先引第三条。输出两篇已引用记录、合并理由和首次出现的新编号。所有书目仅用于演示，未作真实来源核验。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

将稿件和原书目放在同一工作目录，对非连续旧编号提供原编号到文献键的 JSON 映射。

```sh
python3 scripts/citations.py records.json manuscript.md output --labels labels.json
```

output/manuscript.md、cited.csl.json 和逐处编号对照。外部数据库核验另有明确记录。

[完整用法和输入格式](../SKILL.md)

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

用最小样例的文献库，给单独一条原句补上作者选定的 A 条目，然后同步书目。

```sh
python3 scripts/place.py my-example/input/records.json examples/sentence.md examples/placement-plan.json with-citations
python3 scripts/citations.py my-example/input/records.json with-citations/manuscript-cited.md with-library
```
