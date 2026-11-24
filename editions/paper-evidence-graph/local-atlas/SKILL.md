---
name: paper-evidence-graph
description: 单实体关系图册。以指定对象为中心列入边、出边和证据，便于从单个材料或方法读起。
---

# 文献知识图谱

## 单实体关系图册

先按案例要求读原始材料，写出完整的目标产物。以指定对象为中心列入边、出边和证据，便于从单个材料或方法读起。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。保持方向与关系类型；没有出现的对象返回空集。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 追问一篇论文能支持哪条路径

查询中的 source_policy 取 same 时，输出只留下每一步都有同一文献支持的路径。要核对某一篇，在问题 JSON 中填入 source_file。反向查询仍保留原文陈述的主语、关系和宾语。

```sh
python3 scripts/lookup.py examples/field-graph.json examples/one-paper.json --diagram field-figures
```

从实际研究问题着手建图。节点标明类型与文中定义，边保留原方向、条件和逐字引文。同名实体先区分义项，跨论文合并须有依据。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。 以下路径中的材料名按本次输入替换。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/graph.py" /app/work/sources.json /app/work/graph-plan.json /app/output
```

graph.graphml 可继续编辑。单关系查询用 where；从样品经方法追到测量量时用 from 与有序 steps，每步写 predicate，结果列出每一跳的原句。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)

从一个结果反查方法时，可直接查询已导出的 graph.json。每步用 direction 选择 in 或 out；scope_policy 取 same 时，整条路径限于同一实验条件。输出逐步列出原论文陈述的主语、宾语、关系、条件及引句。
