---
name: align-paper-translation
description: 数字与界值对照稿。按分段比较原译文的数字、误差、界值和顺序，可逐条定位漏译或交换的数值。
---

# 文献翻译

## 数字与界值对照稿

先按案例要求读原始材料，写出完整的目标产物。按分段比较原译文的数字、误差、界值和顺序，可逐条定位漏译或交换的数值。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。数字次序变化需结合上下文判断；单位换算另在译文内交代。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 译出测量范围

“At least 3 cm”可译为“至少 3 cm”或“≥ 3 cm”。若译成“> 3 cm”，数值 3 没变，等号处的含义已经变了。核对结果写在 audit.json，逐段译稿在 bilingual.md。

```sh
python3 scripts/prose.py translate examples/crest-source.json examples/crest-draft.json translation --strict
```

按原文顺序交付指定范围内的双语对照。每段保留段号，图注、表头、公式和引用编号沿用原稿。译文主动核对否定、适用范围、比较方向、数值和单位；同一术语采用同一译法，语义不同的同名术语分列。

读取本次材料、任务说明和指定交付格式。短文或已有稿件可以直接编辑。长文、多附件或数字密集时，从文件名、页、段、表格单元格建立证据索引。Word 表格保留表号、行号和列号；带单位的值要同时核对同表列头。长文可先按段建立对照，再核对遗漏、原文变动和术语。具体调用见[处理方法](references/method.md)。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

长论文可用 `casework.py find 检索词 --source 实际文件名` 查找带位置的原文。多个检索词要在同一条材料里同时出现；结果列出原句和总命中数。

把题目要求的成稿写到 `/app/output`，用原始 `case_id` 和 `output_contract` 规定的字段与类型生成 `result.json`。依据、局限和需作者确认的事项放在题目对应字段。要求可编辑文件或渲染预览时，交付实际生成的文件。

已有符合要求的 `result.json` 可直接运行 `casework.py check`。需要把成品填入结果时，先把自行撰写的字段放入 `/app/work/fields.json`。下面示例把相对文件路径写入 `/editable`；运行时换成本题的字段名和实际文件名。题目要求正文或数组时，分别用 `--text 字段 文件` 或 `--json 字段 文件 'JSON指针'`，整份 JSON 的指针为 `''`。所引用的文件均相对输出目录。

```sh
python3 "$S/scripts/casework.py" deliver --fields /app/work/fields.json --file /editable bilingual.md
```

[本地示例与输入输出](examples/README.md)

同段比较多个实验组时，把组名和译名写入 glossary。译文可以调换分句。对照表 audit.json 按组列出原值与译值，能区分换序表达和错配结果。带“分别”的并列报告也可核对。
