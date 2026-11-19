# 文献文档解析

双栏 PDF、合并表头或带扫描页的论文。按阅读顺序取得正文，保留表格、列单位和页码。

## 试用示例

生成两页双栏 PDF，交错写入左右栏文本，另放重复页眉。输出应先读完左栏，再读右栏；两页页眉保存在 marginalia。PDF 用标准库生成。解析需原环境的 PyMuPDF 或 Poppler。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把论文 PDF 交给本工具。已有 Python 与 PyMuPDF 时可直接运行。

```sh
python3 scripts/parse_pdf.py paper.pdf output/layout.json
```

output/layout.json 和同名 TXT。表外列名保存在 external_header，网格内的数据行仍按原顺序读取。若一个网格行中并列多组测量，可在 aligned_measurements 中按原表行名读取数值；如 10¹⁹ 的上标仍有原始文字可追溯。

[完整用法和输入格式](../SKILL.md)
