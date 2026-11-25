# 原文与配对数据合读 · 使用示例

这里的短文和数据均为自拟的使用示例。

三个秋季测站中两站能配对。北站从 1.20 cm 到 9 mm，差为 −3 mm；东站从 0 到 2 mm，百分比留空；西站缺复测。均差为 −0.5 mm。

在本作品目录用 Python 3.9 或以上版本运行。
文本输入和网页导出使用 Python 标准库。 PDF 与 Excel 输入分别可选装 PyMuPDF 与 openpyxl。

```sh
python3 scripts/paired_readings.py sample/sources sample/plan.json /tmp/paired-readings-example
```

notebook.html 收录章节和重算结果，notes.json 可检索每个判断的原句，pairs.tsv 列出两个原始行号、配对差与相对变化。

本例需要改动输入时，可复制 sample/sources 与 plan.json。按题目实际材料核对输入引文或坐标，再根据文章内容撰写译文、笔记或断言。
