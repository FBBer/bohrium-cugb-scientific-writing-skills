---
name: evidence-notebook
description: 沿论文真实结构建立含研究条件、发现和局限的笔记卡片、可检索主题索引及逐条证据映射。
---

# 结构化阅读笔记

沿论文原有章节和讨论顺序建立骨架。辨别经验论文、理论推导、方法稿或综述；根据体裁取证。先列每节在论证中的作用，再从问题到结论记录原文所述步骤。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。先核查原材料能否支持问题，将明确要求的输出字段、类型、语言和文件名记在工作目录。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

工作计划是 {"language":"zh","sections":[{"title":"真实章节名","paragraphs":[[{"id":"N1","role":"finding","text":"该条发现和边界","condition":"成立条件","keywords":["检索词"],"evidence":[{"id":"索引锚点","quote":"逐字证据"}]}]]}]}。合法角色 question、data、method、finding、limitation、definition、context、interpretation。paragraphs 的外层为段落、内层为句子或笔记项。摘要应重述论文实际问题、材料范围、关键条件、主要结果和作者承认的局限。用章节间的依赖解释为何下一部分出现。

把数值与单位、比较对象、评价指标和实验设定绑定；分开写参数与结论、观察与作者解释。对同一结果的正文和图表数值分别取证，有差异就写清各自位置和可疑原因。用一致的索引词串起缩写与同义词；跨论文比较时区分真实可比字段与不可比条件。给每条缺失信息设置 status=unreported 或 uncertain 并说明 reason；推断标 inference、给出依据。

```sh
python3 "$S/scripts/compose.py" notes /app/work/sources.json /app/work/notes-plan.json /app/output
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

## 交付与复核

检查来源映射中的每一条引文，重点检查主要发现、方法边界以及结论可能失效的条件。交付可读笔记、主题索引和主张溯源表，并在 case 的字段中给出真实卡片和未决项。

先将已完成的真实部分保存到 /app/output，逐轮补齐。将主结果本身写入 /app/output/result.json，保持原 case_id、原 output_contract 的全部字段、类型和层级。原契约禁止额外字段时把审计放在旁文件。明确标记缺材料、原文未报告、证据冲突和工具失败，附已完成范围、证据定位、未决项与实际改动。Office 或图形有要求时同时保留真正可编辑源和渲染预览。最后运行下方契约检查并打开每个必需产物。脚本只查结构，仍需以原文判断主结果。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/evidence-notebook-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
