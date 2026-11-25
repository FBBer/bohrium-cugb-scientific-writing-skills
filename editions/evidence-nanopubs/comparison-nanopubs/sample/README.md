# 把成对观测发布为 Nanopublication · 使用示例

这里的短文和数据均为自拟的使用示例。

干板条件下 A 记录 0.8 cm、B 记录 6 mm。统一为毫米得到 B − A = −2 mm。两个测量引文及条件声明分别出现在出处图中。

在本作品目录用 Python 3.9 或以上版本运行。
生成 TriG 使用 Python 标准库。独立读取可用 python3 -m pip install rdflib 安装 RDFLib。 PDF 与 Excel 输入分别可选装 PyMuPDF 与 openpyxl。

```sh
python3 scripts/comparison_nano.py sample/sources sample/plan.json /tmp/comparison-nanopubs-example
```

comparisons.trig 可被独立 RDF 解析器打开。每个断言的引用可追到原句、位置、版本和原文件指纹。comparisons.json 和比较表便于复核哪一组是参照。

本例需要改动输入时，可复制 sample/sources 与 plan.json。按题目实际材料核对输入引文或坐标，再根据文章内容撰写译文、笔记或断言。
