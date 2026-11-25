# 随论文修订的阅读笔记 · 使用示例

这里的短文和数据均为自拟的使用示例。

加载试验的修订稿把采样段移了一行，把 B 次位移从 18 mm 改为 15 mm。阅读页分别更新定位与结论，并保留旧值的出处。

在本作品目录用 Python 3.9 或以上版本运行。
文本输入和网页导出使用 Python 标准库。 PDF 与 Excel 输入分别可选装 PyMuPDF 与 openpyxl。

```sh
python3 scripts/edition_notes.py sample/sources sample/plan.json /tmp/edition-notes-example
```

notebook.html 将当前结论摆在原章节下。展开“上版记载”可以看到数值为何改变；notebook.md 可在普通笔记软件里继续写，notes.json 保留两版的文件、行与原句。

本例需要改动输入时，可复制 sample/sources 与 plan.json。按题目实际材料核对输入引文或坐标，再根据文章内容撰写译文、笔记或断言。
