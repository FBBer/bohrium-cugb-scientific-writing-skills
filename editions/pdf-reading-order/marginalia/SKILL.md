---
name: pdf-reading-order
description: 页边重复文字分离。用文字位置和跨页复现率找出运行页眉、页脚，保留每一次出现的位置。
---

# 文献文档解析

## 页边重复文字分离

先按案例要求读原始材料，写出完整的目标产物。用文字位置和跨页复现率找出运行页眉、页脚，保留每一次出现的位置。

该工具直接读取实际材料。版面分析需有 PDF 并安装 PyMuPDF。

```sh
python3 examples/edition/make_pdf.py
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。只把页边重复文字列为候选，正文里的重名标题继续保留。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 分清表里的读数、上限和空白

仪器表把单位另起一行。上游的 1.2 ± 0.3 cm 分成读数和不确定度两列，中游的 < 0.2 cm 保留为严格上限。中游的传播时间留空，表注可从相应单元格回看。

```sh
python3 examples/gauge_table.py field/gauges.pdf
python3 scripts/parse_pdf.py field/gauges.pdf field/layout.json
python3 scripts/open_tables.py field/layout.json --row Midstream --column Offset
```

## 取出论文表格

运行 `parse_pdf.py` 后，同目录的 `layout.tables.tsv` 可用表格软件打开。每格保留物理页、行名、列名、原始数值、页内坐标及检测到的脚注。带表题的无框数值表按字形位置和行列对齐恢复；空白格保留空值。没有足够行、标题或列间距时，保留原页文字，避免把两栏正文误认成表。要核对某个数值，打开原页视图，点选相应的表格行列。也可按行名、列名直接查询，得到数值、物理页、原页位置和脚注。若有多个同名读数，指定 `--page` 或 `--table`。下面是自拟的仪器示例。

```sh
python3 examples/unruled.py trial/stations.pdf
python3 scripts/parse_pdf.py trial/stations.pdf trial/layout.json
python3 scripts/open_tables.py trial/layout.json --row North --column 'Offset (mV)'
python3 scripts/atlas.py trial/stations.pdf trial/layout.json trial/atlas.html
```

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
