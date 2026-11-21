---
name: reconcile-citations
description: 校验稿件引文与书目、保守去重、按首次出现重排编号并输出可编辑 CSL JSON 和逐处审计。
---

# 参考文献与引用管理

在原稿中找到原编号和对应文末条目，再与文献库核对。按首次引用顺序更新正文、图表和附录，不要让文献库的导出顺序改变引用身份。DOI 和题名相互矛盾或出现多个匹配时保留原稿并指出哪条需确认。

读取本次材料、任务说明和指定交付格式。短文或已有稿件可以直接编辑。长文、多附件或数字密集时，从文件名、页、段、表格单元格建立证据索引。Word 表格保留表号、行号和列号；带单位的值要同时核对同表列头。数值编号稿可由脚本用原表的 DOI 或唯一题名找回文献键；有作者给定的编号表时优先用该表。具体调用见[处理方法](references/method.md)。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

长论文可用 `casework.py find 检索词 --source 实际文件名` 查找带位置的原文。多个检索词要在同一条材料里同时出现；结果列出原句和总命中数。

把题目要求的成稿写到 `/app/output`，用原始 `case_id` 和 `output_contract` 规定的字段与类型生成 `result.json`。依据、局限和需作者确认的事项放在题目对应字段。要求可编辑文件或渲染预览时，交付实际生成的文件。

已有符合要求的 `result.json` 可直接运行 `casework.py check`。需要把成品填入结果时，先把自行撰写的字段放入 `/app/work/fields.json`。下面示例把相对文件路径写入 `/editable`；运行时换成本题的字段名和实际文件名。题目要求正文或数组时，分别用 `--text 字段 文件` 或 `--json 字段 文件 'JSON指针'`，整份 JSON 的指针为 `''`。所引用的文件均相对输出目录。

```sh
python3 "$S/scripts/casework.py" deliver --fields /app/work/fields.json --file /editable manuscript.md
```

[本地示例与输入输出](examples/README.md)
