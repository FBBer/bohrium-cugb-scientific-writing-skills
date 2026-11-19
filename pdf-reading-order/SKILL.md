---
name: pdf-reading-order
description: 从真实论文 PDF 恢复阅读顺序、正文、表格、公式和题注。用于需要物理页与版面坐标可复查的学术文档解析。
---

# 文献文档解析

从 case.json 和 task.md 确认可交付的页段、格式、需要回答的问题。用原 PDF 的物理页序号，另列印刷页码。对完整论文建目录，标出题名、作者/单位、摘要、各级标题、正文、图表题注、脚注、参考文献。若指定页段，保留范围内的全部内容和跨页衔接。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

解析器优先使用 PyMuPDF，备用 Poppler 的 pdftotext -bbox-layout。按页输出行、左上坐标原点的点数、字体片段、候选栏区及页边文字。整页图片或稀疏文字页面使用 Tesseract 的行框和最低词置信度，混合页保留原文字层。先用 tesseract --list-langs 选已安装且与原文一致的语言。依赖缺少时保留可读页、渲染未读页并记录失败位置。

先查看缩略页和列间空白，再沿页面阅读。跨栏标题/图/表将版面划成上下带，每个带内先左栏自上而下再右栏。三栏、侧栏或没有可靠间隔的页要根据渲染检查阅读图，必要时手动调序。页边文字另存，不能仅凭顶部位置丢弃标题。跨页续段只在语法和几何均支持时连接，同时保留两页的行号。

为每个表恢复表头层数、行列号、跨行跨列、单位、脚注和续表对应。优先获取原始网格，复核空值与 0、缺失与不适用。PDF 表检测不到或未带合并信息时查看局部放大并输出 HTML rowspan/colspan 或带起止坐标的 JSON。图表位置以边框及题注锚定。用字体大小及基线恢复上下标，单独核对希腊字母、负号、运算符及公式编号。保留原文与规范化表示两份，明确无法辨认的符号。

```sh
python3 "$S/scripts/parse_pdf.py" "/input/实际文件.pdf" "/app/work/layout.json" --lang eng
```

## 交付与复核

抽查第一页、末页、栏切换页、跨页表和不确定符号的裁片，逐项核对对象数、文本顺序、行列归属。统计已检查页、表格数、未决行。将可编辑解析结果、目录、问题答案及对应页框放到指定字段，附原稿位置。文字层检查无法验证公式时保留裁片。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

独立环境可安装 Python 包 PyMuPDF（本地实测 2.1），或系统 Poppler 的 pdftotext/pdftoppm；OCR 实测 Tesseract 5.5.2，需要对应的语言数据。用 python3 -m pip install PyMuPDF 安装到运行脚本的同一个解释器，然后先执行 python3 -c "import pymupdf"。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/pdf-reading-order-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
