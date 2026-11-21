---
name: audit-academic-edits
description: 润色科研稿件并逐处记录改前、改后、理由与语义核查，适用于中英文摘要、论文和审稿回复。
---

# 学术语言润色

把改好的完整正文交给作者，逐条说明实质改动。保留原有数据、限定、公式和引用，尤其留意同一句里对应不同样品的数值。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。只交文本时可省略 Word 和 PDF 两个选项。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
python3 "$S/scripts/segments.py" /app/work/sources.json paper.docx /app/work/segments.json
python3 "$S/scripts/prose.py" edit /app/work/segments.json /app/work/revisions.json /app/output --word --preview
```

原句与修改稿用 id 对齐。改动条目给 target、type、reason。--word 生成清稿和可逐条接受或拒绝的 Word 修订稿。要保留原件样式、表格与脚注，可追加 --original-docx 原稿路径，并用 Word 段落定位。

按 Word 原段改稿时，--original-docx /input/paper.docx 会保留句中原有的公式、链接与自动编号，周围文字可以正常修订。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
