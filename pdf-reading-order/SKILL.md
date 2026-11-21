---
name: pdf-reading-order
description: 从真实论文 PDF 恢复阅读顺序、正文、表格、公式和题注。用于需要物理页与版面坐标可复查的学术文档解析。
---

# 文献文档解析

先按题目点名的页、表或公式做解析，保留段落的物理页、栏、坐标和版面顺序。表中读数带上行名、列名、单位与脚注，公式保留上下标。扫描区域需要识别，读不清的字符给出原页位置。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/parse_pdf.py" /input/paper.pdf /app/output/layout.json
```

实际 PDF 路径取自本题。layout.json 的 pages 保留原行和网格，structure.continued_tables 将相邻页、同表号、同表头且明确写有续表的记录连接，每个值仍带原页和单元格位置。

需要连续正文时，读取 layout.json 中的 structure.paragraphs。每个段落给出物理页码、逐行位置和字符范围，双栏各自连接。

需要对照版面时，解析完成后运行 `python3 "$S/scripts/atlas.py" paper.pdf layout.json source-atlas.html --pages 1,3-5`。在浏览器打开 HTML，点选文字、表格或图片即可在对应原页上定位。省略 --pages 可查看全文。需要 PyMuPDF。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
