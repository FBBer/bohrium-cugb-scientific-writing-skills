# 文献总结与结构化笔记

需要复用的论文摘录、实验观察与研究限制。得到能回到原句的阅读笔记，并按主题或论文比较。

## 试用示例

自写的观测报告包括方法、发现和限制。检验章节顺序、可检索关键词、每句引文以及读数的单位，额外篡改过的引文应被发现。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

打开 `my-example/river-notes/notebook.html` 阅读水尺观测。页首可比较两处同为 0.7 cm 的读数及其各自的水情，页底可打开原文、章节笔记和论文对照表。`my-example/output/reading.html` 展示另一份按作者提纲整理的笔记，其输入和提纲分别在 `my-example/input/` 和 `my-example/work/`。

## 换成自己的材料

把论文和想回答的问题交给加载该工具的 Agent。材料索引与笔记计划的结构见示例中的 work 目录。

```sh
python3 scripts/compose.py notes work/sources.json work/notes-plan.json output --strict
```

output/notes.md、paper-cards.json 和主题索引。论文事实与读者解释分别标明。

[完整用法和输入格式](../SKILL.md)

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

导出这个样例的 Word 和 PDF，点笔记中的序号可阅读证据。

```sh
python3 scripts/compose.py notes my-example/work/sources.json my-example/work/notes-plan.json my-example/output --word --preview
```

## 同一个 0.7 cm，分别说明什么

```sh
python3 scripts/notebook.py examples/river river-notes --table 'river-stage.md=readings.tsv'
python3 scripts/recall.py river-notes search '0.7' --section 上游浅滩 --role finding --originals examples/river
python3 scripts/recall.py river-notes table readings.tsv --where 测站=深槽 --where 水情=退水 --where 测次=2 --field '偏差 (cm)'
```

打开 river-notes/notebook.html。上游与下游各有一条 0.7 cm，上游只观测涨水，下游只观测退水。第一条查询只取上游小节及其条件；第二条查询会返回原表第 5 行第 4 列的 0.0。删掉测次条件会看到两次深槽读数。空单元格在查询中保留为空。

## 比较多篇论文

```sh
python3 scripts/notebook.py examples/papers reading-notes --focus 漂移 --focus drift
```

reading-notes/study-matrix.tsv 按研究问题、方法、发现、解释和局限并排组织论文；comparison.tsv 保留原文段落与字符区间。阅读区使用 --language en 可切换英文栏目。原文引句保持原语种。
