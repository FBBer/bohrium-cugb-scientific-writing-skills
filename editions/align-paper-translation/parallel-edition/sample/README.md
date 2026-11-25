# 按原文逐段翻译 · 使用示例

这里的短文和数据均为自拟的使用示例。

四段示例里，两处分指仪器和水位的 level 分别译为“水准仪”和“水位”。最后两段保留“不超过 3 mm [4]”和对渗漏判断的限定。

在本作品目录用 Python 3.9 或以上版本运行。
Word 导出使用 python-docx，可用 python3 -m pip install python-docx 安装。无此依赖时照常生成网页与文本。 PDF 与 Excel 输入分别可选装 PyMuPDF 与 openpyxl。

```sh
python3 scripts/parallel_edition.py sample/sources sample/plan.json /tmp/parallel-edition-example
```

translation.txt 是连续译文。parallel.html 将同一语义组并排显示，alignment.json 保存段号、术语和数量差异。安装 python-docx 后还会生成可编辑的 parallel.docx。

本例需要改动输入时，可复制 sample/sources 与 plan.json。按题目实际材料核对输入引文或坐标，再根据文章内容撰写译文、笔记或断言。
