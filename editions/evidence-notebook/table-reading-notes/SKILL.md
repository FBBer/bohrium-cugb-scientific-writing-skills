---
name: evidence-notebook
description: 整理章节与关键结果，把发现从论文原句一路定位到随文表格的原始单元格。
metadata:
  author: GPT-6.2Astra
---

# 从表格原格读论文

按实际章节摘要，读出数据来源、实验设计和作者写明的边界。指向数据表的笔记给出对应原句，cells 列出文件、列名和唯一的行条件 where（支持多列组合）。可用 unit_column 引用同一行的单位。上限、误差、零、空白和 ND 保留原义；空白的原因只有在论文明确说明时才补入笔记。重复行先查样本编号，不能任意取第一行。

## 使用本题材料

读取 /input/case.json、task.md 和列出的附件。把示例命令中的输入换成本题实际文件。将主结果按场景指定的字段和文件名写入 /app/output，保留原 case_id、来源和不确定项。完整的通用处理入口见 [FULL_WORKFLOW.md](FULL_WORKFLOW.md)。

```sh
python3 scripts/table_notes.py sample/sources sample/plan.json /tmp/source-cells
```

notebook.html 展示笔记与原表格，cells.json 保留每格的行列和记录类型。示例分别读出零值、<0.2 mm、1.4 ± 0.1 mm 和空白。

[打开示例成品](sample/preview/notebook.html)。sample/ 使用自拟材料。文本处理需要 Python 3.9 或以上；Word、PDF、Excel 的可选依赖和通用工作流见随附说明。

作品署名　GPT-6.2Astra
