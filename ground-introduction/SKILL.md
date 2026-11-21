---
name: ground-introduction
description: 用限定来源组织研究背景、比较既有工作、推导有范围的空白，并把贡献逐项对应本文证据。
---

# 引言与相关工作写作

从作者自己的问题、材料和贡献出发写成一篇连贯引言。用具体论文对比对象、方法、条件和限制；从这些差异推出有边界的空白，并落到本研究实际完成的内容。引文与它支撑的句子放在一起。

读取本次材料、任务说明和指定交付格式。短文或已有稿件可以直接编辑。长文、多附件或数字密集时，从文件名、页、段、表格单元格建立证据索引。Word 表格保留表号、行号和列号；带单位的值要同时核对同表列头。多篇文献之间容易混淆条件时，用比较表把对象、指标、结果与出处并排。具体调用见[处理方法](references/method.md)。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

长论文可用 `casework.py find 检索词 --source 实际文件名` 查找带位置的原文。多个检索词要在同一条材料里同时出现；结果列出原句和总命中数。

把题目要求的成稿写到 `/app/output`，用原始 `case_id` 和 `output_contract` 规定的字段与类型生成 `result.json`。依据、局限和需作者确认的事项放在题目对应字段。要求可编辑文件或渲染预览时，交付实际生成的文件。

已有符合要求的 `result.json` 可直接运行 `casework.py check`。需要把成品填入结果时，先把自行撰写的字段放入 `/app/work/fields.json`。下面示例把相对文件路径写入 `/editable`；运行时换成本题的字段名和实际文件名。题目要求正文或数组时，分别用 `--text 字段 文件` 或 `--json 字段 文件 'JSON指针'`，整份 JSON 的指针为 `''`。所引用的文件均相对输出目录。

```sh
python3 "$S/scripts/casework.py" deliver --fields /app/work/fields.json --file /editable introduction.md
```

[本地示例与输入输出](examples/README.md)
