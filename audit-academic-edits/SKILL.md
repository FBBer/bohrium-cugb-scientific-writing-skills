---
name: audit-academic-edits
description: 润色科研稿件并逐处记录改前、改后、理由与语义核查，适用于中英文摘要、论文和审稿回复。
---

# 学术语言润色

先确定稿件目标语言、文体、读者及是否有期刊规范。为每段/句保留稳定编号，列出必须保持的术语、研究主体、样本、方法、方向、数量、单位、引用、图表和结论的适用条件。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。先核查原材料能否支持问题，将明确要求的输出字段、类型、语言和文件名记在工作目录。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

segments.json 使用 {"segments":[{"id":"P1","location":"原稿第1段","text":"原稿句子"}],"glossary":{"出现的术语":"约定写法"}}。edits.json 是 [{"id":"P1","target":"修订文本","type":"修改类型","reason":"针对本句的修改原因"}]。每个原段都列入，包括直接保留的段落。先解决语法、主谓和悬垂修饰，再处理信息主语、单位符号、术语首现和长句分解。选择符合研究语域的词，保留作者声音。必要的重排应保留指代先行词和信息依赖。

每个修改过的段落记录类型和具体理由。若同段有多项不同动机，按句或子句另列逐处说明，从字符差异回连到原句。分别复核比较基线、否定范围、因果/相关、量词、置信表述、时态及适用条件。笼统地把所有 may 改成 demonstrate 会改变证据强度。含义不明时保留可读原句，另列可供作者判断的释义。用户要求改写缩写、翻译数字格式或单位时，记录等价依据。

脚本生成可编辑的 revised.md 与逐字符偏移映射、保护项计数、词表和审校线索。语法改好但研究结论失真的句子返回再修。需要 DOCX 时生成真正可编辑的稿件，并渲染成 PDF/PNG 检查图表、脚注和上标。

```sh
python3 "$S/scripts/prose.py" edit /app/work/segments.json /app/work/edits.json /app/output
```

## 交付与复核

从原文到修订稿和反向各读一次，确认每个引用、数字、图表指向与研究对象仍匹配。交付完整干净稿、改动表、术语约定和未决问题。将实际案例输出写入需求指定字段。

先将已完成的真实部分保存到 /app/output，逐轮补齐。将主结果本身写入 /app/output/result.json，保持原 case_id、原 output_contract 的全部字段、类型和层级。原契约禁止额外字段时把审计放在旁文件。明确标记缺材料、原文未报告、证据冲突和工具失败，附已完成范围、证据定位、未决项与实际改动。Office 或图形有要求时同时保留真正可编辑源和渲染预览。最后运行下方契约检查并打开每个必需产物。脚本只查结构，仍需以原文判断主结果。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/audit-academic-edits-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
