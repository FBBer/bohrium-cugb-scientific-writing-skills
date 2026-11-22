---
name: paper-evidence-graph
description: 抽取可溯源的实体及有向关系，保留有证据的别名对齐和冲突，导出可查询的 JSON 与 GraphML。
---

# 文献知识图谱

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
