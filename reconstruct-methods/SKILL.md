---
name: reconstruct-methods
description: 把配置、代码、日志和论文转为可复核的方法实验章节，协调配置冲突并记录复现所需设置。
---

# 方法与实验章节写作

按实验实际顺序写成可以照做的章节，写清样品或数据进入哪一步、经过何种操作、产出什么。设置依运行编号、训练或测试阶段分开；同一条件下日志与配置确有差异时并列取值、单位和来源。保留复现实验需要的命令与版本。

读取本次材料、任务说明和指定交付格式。短文或已有稿件可以直接编辑。长文、多附件或数字密集时，从文件名、页、段、表格单元格建立证据索引。Word 表格保留表号、行号和列号；带单位的值要同时核对同表列头。有多份运行记录时，参数工具可按运行与阶段区分差异；工具只列待解释之处，正文采用能由该次运行证明的值。具体调用见[处理方法](references/method.md)。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

长论文可用 `casework.py find 检索词 --source 实际文件名` 查找带位置的原文。多个检索词要在同一条材料里同时出现；结果列出原句和总命中数。

把题目要求的成稿写到 `/app/output`，用原始 `case_id` 和 `output_contract` 规定的字段与类型生成 `result.json`。依据、局限和需作者确认的事项放在题目对应字段。要求可编辑文件或渲染预览时，交付实际生成的文件。

已有符合要求的 `result.json` 可直接运行 `casework.py check`。需要把成品填入结果时，先把自行撰写的字段放入 `/app/work/fields.json`。下面示例把相对文件路径写入 `/editable`；运行时换成本题的字段名和实际文件名。题目要求正文或数组时，分别用 `--text 字段 文件` 或 `--json 字段 文件 'JSON指针'`，整份 JSON 的指针为 `''`。所引用的文件均相对输出目录。

```sh
python3 "$S/scripts/casework.py" deliver --fields /app/work/fields.json --file /editable methods.md
```

[本地示例与输入输出](examples/README.md)
