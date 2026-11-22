---
name: audit-academic-edits
description: 润色科研稿件并逐处记录改前、改后、理由与语义核查，适用于中英文摘要、论文和审稿回复。
---

# 学术语言润色

## 保留临界值

“At most 5 cm”可以压缩为“≤ 5 cm”。改成“< 5 cm”会排除恰好为 5 cm 的情形。修订稿写入 revised.md，改前、改后和每处理由在 audit.json。

```sh
python3 scripts/prose.py edit examples/gauge-source.json examples/gauge-draft.json revision --strict
```

先确定稿件目标语言、文体、读者及是否有期刊规范。为每段/句保留稳定编号，列出必须保持的术语、研究主体、样本、方法、方向、数量、单位、引用、图表和结论的适用条件。

## 材料与出处

从 `/input/case.json` 和 `task.md` 确定交付内容及格式。用下列命令给附件建立索引，按文件名、页码或行号找原文。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

## 处理实际材料

segments.json 使用 {"segments":[{"id":"P1","location":"原稿第1段","text":"原稿句子"}],"glossary":{"出现的术语":"约定写法"}}。edits.json 是 [{"id":"P1","target":"修订文本","type":"修改类型","reason":"针对本句的修改原因"}]。每个原段都列入，包括直接保留的段落。先解决语法、主谓和悬垂修饰，再处理信息主语、单位符号、术语首现和长句分解。选择符合研究语域的词，保留作者声音。必要的重排应保留指代先行词和信息依赖。

每个修改过的段落记录类型和具体理由。若同段有多项不同动机，按句或子句另列逐处说明，从字符差异回连到原句。分别复核比较基线、否定范围、因果/相关、量词、置信表述、时态及适用条件。笼统地把所有 may 改成 demonstrate 会改变证据强度。含义不明时保留可读原句，另列可供作者判断的释义。用户要求改写缩写、翻译数字格式或单位时，记录等价依据。

脚本生成可编辑的 revised.md 与逐字符偏移映射、保护项计数、词表和审校线索。语法改好但研究结论失真的句子返回再修。需要 DOCX 时生成真正可编辑的稿件，并渲染成 PDF/PNG 检查图表、脚注和上标。

```sh
python3 "$S/scripts/prose.py" edit /app/work/segments.json /app/work/edits.json /app/output --strict
```

否定词数量相同仍可能改变含义。逐句对照否定词实际支配的动作，特别留意“未发生漂移”与“未停止漂移”、“无法排除”与“已经排除”。审计报告含数量或语义待核项时，可加 --strict 使程序返回非零；审定的翻译变体应保留判断依据。

## 交付与复核

从原文到修订稿和反向各读一次，确认每个引用、数字、图表指向与研究对象仍匹配。交付完整干净稿、改动表、术语约定和未决问题。将实际案例输出写入需求指定字段。

成稿放在 /app/output，沿用 case.json 中的 case_id 和 output_contract，按 task.md 命名。原文出处及待核对事项写在相应字段。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。依赖版本见示例说明。

## 示例

从本目录运行 `python3 examples/demo.py /tmp/audit-academic-edits-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
