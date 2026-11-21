---
name: build-latex-manuscript
description: 在实际模板上修复和编译可编辑的 LaTeX 稿件，检查公式、引用、表格、日志和 PDF。
---

# LaTeX 写作与编译

先找实际主文件、投稿模板及作者指定的引擎。保留原目录、图、书目和宏，在副本上完成改稿。交付可重编的源码和本次生成的 PDF，并逐项核对题目点名的公式、引用、表格或版式。

读取本次材料、任务说明和指定交付格式。短文或已有稿件可以直接编辑。长文、多附件或数字密集时，从文件名、页、段、表格单元格建立证据索引。Word 表格保留表号、行号和列号；带单位的值要同时核对同表列头。编译工具会保留日志，遇到子目录主稿会根据缺文件诊断重试正确的工作目录。指定引擎与模板冲突时保留原诊断。具体调用见[处理方法](references/method.md)。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

长论文可用 `casework.py find 检索词 --source 实际文件名` 查找带位置的原文。多个检索词要在同一条材料里同时出现；结果列出原句和总命中数。

把题目要求的成稿写到 `/app/output`，用原始 `case_id` 和 `output_contract` 规定的字段与类型生成 `result.json`。依据、局限和需作者确认的事项放在题目对应字段。要求可编辑文件或渲染预览时，交付实际生成的文件。

已有符合要求的 `result.json` 可直接运行 `casework.py check`。需要把成品填入结果时，先把自行撰写的字段放入 `/app/work/fields.json`。下面示例把相对文件路径写入 `/file`；运行时换成本题的字段名和实际文件名。题目要求正文或数组时，分别用 `--text 字段 文件` 或 `--json 字段 文件 'JSON指针'`，整份 JSON 的指针为 `''`。所引用的文件均相对输出目录。

```sh
python3 "$S/scripts/casework.py" deliver --fields /app/work/fields.json --file /file latex-build/manuscript.pdf
```

[本地示例与输入输出](examples/README.md)
