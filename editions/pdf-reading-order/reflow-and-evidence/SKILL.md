---
name: pdf-reading-order
description: 从科研 PDF 恢复正文阅读顺序、表格、章节和公式，给每段保留原页与坐标。用于多栏论文、跨页续表、图文混排或扫描件的解析和定位。
---

# 从阅读顺序回到原页

在 Skill 所在目录运行下面的命令。它会打开本次案例实际给出的每份 PDF，写出可阅读的正文、逐行依据和按原文件区分的版面数据。

~~~sh
python3 run.py
~~~

## 按案例交稿

1. 先读 `/input/task.md` 和 `/input/case.json`。记下要求解析的论文、页段、交付字段和格式。多个附件同名时用相对路径区分。只处理其中一篇可加 `--pdf materials/paper.pdf`。
2. 打开 `/app/output/document.md` 顺读正文。打开 `/app/output/evidence.json` 以 `file + page + line` 回到原件。坐标单位为 PDF 点，原点在旋转前页面左上角。`folio.physical` 从 1 开始，`printed` 为纸面印的页码，`pdf_label` 为 PDF 内置页签。
3. 在各篇 `documents/*/layout.json` 查具体结构。`pages[].tables` 保留原网格、物理行列及单元格坐标，合并单元格的空位保留。`continued_tables` 列出续表各行的原页。`structure.objects` 把图表题注和正文提及分开。`structure.headings` 包含显式层级或字号依据，页眉页脚在 `marginalia`。行的 `text` 仍是原始转写，排版上下标另见 `display_text` 和 `spans`。
4. 核对题目点名的图、表、公式或容易串栏的区域。对缺字、无法还原的二维公式或图片表格，记录原页坐标和可辨部分，可直接打开原 PDF。用 `--find "calibration before"` 查一处原文，跨页断词会给出两处位置。在实际排版可用 PyMuPDF 时，`python3 scripts/atlas.py --help` 可生成逐页对照图册。
5. 交付 `/app/output/result.json`。它保留原 `case_id` 并按案例结构填值。涉及标题作者、参考文献条目、特定公式或自定义嵌套字段时，从前述定位读取原文，将该案例要求的完整字段对象写入 `/app/work/fields.json`，再运行 `python3 run.py --fields /app/work/fields.json`。相同选项在两次调用中保持一致。字段名、类型或必填项不符时，详见 `/app/work/contract-review.json`，原始提取保存在 `extracted.json`。对缺页、疑读、材料冲突分别标出位置及原因。

## 一份可以复现的小样

~~~sh
python3 examples/make_sample.py /tmp/shore/input
python3 run.py --input /tmp/shore/input --work /tmp/shore/work --output /tmp/shore/out --find "calibration before"
~~~

样例生成器绘制两页带栏的虚构现场记录。第一页纸面页码是 17，第二页是 18。样例的 `structure.cross_page_words` 把 `calibra-` 和 `tion` 连回各自原行，`passage_matches` 可在 `work/extracted.json` 查看。测试新材料时，把输入目录换成自己的文件夹。

Python 3.9+。推荐 PyMuPDF 1.24+（`python3 -m pip install pymupdf`）。没有 PyMuPDF 时使用 Poppler 的 `pdftotext`；网格与上标细节取决于可用的后端。扫描页使用本地 Tesseract 与相应语言包，可用 `--lang chi_sim+eng`。表格跨页无表头时，只有邻页同号续表、列界和数值列相符才合并。公式图形、手写和密集叠字应对照页面读。使用 Python 自带模块即可检查多数常见交付结构，可选 `jsonschema` 支持完整 JSON Schema。

作者模型 GPT-6.2Astra。公开源码位置见同目录 `GITHUB_URL.txt`。
