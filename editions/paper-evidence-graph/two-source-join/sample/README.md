# 从两篇论文查共同证据 · 使用示例

这里的短文和数据均为自拟的使用示例。

遮阴时，两种仪器都观察到板的倾斜。镜片漂移还有一篇相反记录，会单独列出；日照下的框架挠曲不会混入答案。

在本作品目录用 Python 3.9 或以上版本运行。
文本输入和网页导出使用 Python 标准库。 PDF 与 Excel 输入分别可选装 PyMuPDF 与 openpyxl。

```sh
python3 scripts/two_source_join.py sample/sources sample/plan.json /tmp/two-source-join-example
```

answers.html 先显示答案，再列两篇论文的原句。graph.graphml 可在 Gephi 或 yEd 编辑；graph.json 保存别名、方向、冲突和每个答案所用的边。

本例需要改动输入时，可复制 sample/sources 与 plan.json。按题目实际材料核对输入引文或坐标，再根据文章内容撰写译文、笔记或断言。
