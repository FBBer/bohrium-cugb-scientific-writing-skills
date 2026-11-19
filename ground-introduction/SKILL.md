---
name: ground-introduction
description: 用限定来源组织研究背景、比较既有工作、推导有范围的空白，并把贡献逐项对应本文证据。
---

# 引言与相关工作写作

先分清本研究的稿件、图表、实验记录与外部工作。给每个研究问题建立比较轴，如任务、对象、数据/场景、方法假设、评价口径和局限。阅读本研究实证范围之后再写贡献句。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。先核查原材料能否支持问题，将明确要求的输出字段、类型、语言和文件名记在工作目录。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

输入计划含 language、sections（各含 title、paragraphs），每个 paragraph 由有序句项构成。句项例 {"id":"I1","role":"gap","text":"仅限所比较工作可推出的空白","condition":"比较边界","evidence":[{"id":"S","quote":"最小原文"}]}。角色为 background、comparison、gap、objective、contribution、scope。comparisons 以同一维度列出各工作的 work、axis、method、condition、observed_result、limit 和 evidence。缺项留空并解释，不从另一篇工作借数值。

从具体任务和技术约束导入，按可比的问题/方法分组，每组说明共同点、差异和取舍。对照方法不是综述文章自己的实验，注意区分谁提出、谁引用。各论文的数值只有在数据集、划分、指标、预算相容时才能直接比较。引用写在实际受支持的句末，优先使用题目提供的著者和文献键，补充材料只在授权且可核对时使用。

将空白从比较矩阵的覆盖范围推导；“给定文献尚未报告某场景”优于声称整个领域从未做过。在贡献句描述本文做了哪项具体工作、评估的场景及正文证据，计划中的实验用计划语气。用 status=inference、reason 说明作者判断；避免为成文补造题名、DOI、领先性、成功表现或创新排序。

```sh
python3 "$S/scripts/compose.py" introduction /app/work/sources.json /app/work/intro-plan.json /app/output
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

## 交付与复核

将每个研究空白连回前文比较，将每个贡献连回本文的方法、结果或图表。输出真正可独立阅读的引言和相关工作正文、比较矩阵、论断—引文对应表及未决信息。表中的技术说明留给核验者，正文保持连贯。

先将已完成的真实部分保存到 /app/output，逐轮补齐。将主结果本身写入 /app/output/result.json，保持原 case_id、原 output_contract 的全部字段、类型和层级。原契约禁止额外字段时把审计放在旁文件。明确标记缺材料、原文未报告、证据冲突和工具失败，附已完成范围、证据定位、未决项与实际改动。Office 或图形有要求时同时保留真正可编辑源和渲染预览。最后运行下方契约检查并打开每个必需产物。脚本只查结构，仍需以原文判断主结果。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/ground-introduction-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
