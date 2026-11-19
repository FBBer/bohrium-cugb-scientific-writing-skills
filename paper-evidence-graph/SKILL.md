---
name: paper-evidence-graph
description: 抽取可溯源的实体及有向关系，保留有证据的别名对齐和冲突，导出可查询的 JSON 与 GraphML。
---

# 文献知识图谱

按论文建立文档身份和证据位置。实体至少区分方法、材料/数据、任务、指标、结论和作者；仅创建材料实际提及的对象。关系保持方向、条件、否定、出处及直接/推断/转述强度。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

计划含 nodes、edges 和 queries 三个数组。节点形如 {"key":"a","type":"method","label":"原名","scope":"学科/义项","document":"实际文件","aliases":[],"evidence":[{"id":"S","quote":"原文"}]}。关系含 source、target（局部 key）、predicate、scope、polarity（positive/negative/uncertain）、strength（direct/inference/quoted）、evidence。保留人名重名、全称/缩写的文内定义、不同任务下的同名模型。仅在有合并依据且类型兼容时给后出现的节点 same_as 和 merge_reason。以有证据的别名表保留原文拼写。

将共现、作者提出、经过验证、引用他人发现及推断区分开。相反结果保留各自适用条件。对相对关系写清 A 相对谁、指标越大还是越好。新增文献可用 --previous 读取既有 graph.json，以持久节点 ID 指明同一实体；核查已有边和证据未丢失。

从材料写至少三个真正不同的研究问题，覆盖方法和任务、指标或比较、以及未证实的关系。每项如 {"question":"哪个方法在此设置下与基线比较？","where":{"predicate":"compared_with","scope":"实际设定"},"source_type":"method"}。支持 source、target、predicate、scope、strength、polarity 过滤和 source_type/target_type。脚本返回实际命中子图与证据。多跳问题可按中间节点连接两次查询并列出各跳证据。

```sh
python3 "$S/scripts/graph.py" /app/work/sources.json /app/work/graph-plan.json /app/output
```

每个有依据的查询同时生成可编辑 SVG。实体类型用能清楚区分的蓝、绿、橙等底色表示，文字和轮廓用深色。节点标签来自源数据，箭头从主体指向客体，关系名称在箭头上，适用条件在箭头下。可用 PyMuPDF 时一并导出印刷版 PDF 和 PNG 预览。增量合并时，出处还保留案例标识与文本版本指纹；同一路径同一行的修订分开定位。原始关系保存在 graph.json，绘图代码位于 scripts/diagram.py。中文稿在图中沿用中文实体和关系标签，分组标题直接写该组回答的问题。

## 交付与复核

打开 graph.graphml、graph.json、queries.json，检查每条边有两端，每个回答的证据能回指正文。数字相同或名称相似不构成合并依据。空查询标记材料缺乏支持，追加实际问题的人类可读答案以及出现冲突时的并列解释。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/paper-evidence-graph-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
