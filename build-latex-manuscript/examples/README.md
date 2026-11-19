# LaTeX 写作与编译

含主文件、子文件、参考文献和图片的 LaTeX 工程。得到可交给他人重编的源码与 PDF，缺文件时能找到出错位置。

## 试用示例

从带表格、带标签公式和交叉引用的 LaTeX 源码实际编译出 PDF。脚本检查源文件、PDF 文件头和第二遍引用；需可用的 pdflatex。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

保留项目目录结构，给出论文主文件和需要的引擎。使用本机安装的 TeX 环境运行。

```sh
python3 scripts/build.py project main.tex output/latex-build
```

output/latex-build/manuscript.pdf、source/ 和 compile.log。源码与 PDF 配套保存。

[完整用法和输入格式](../SKILL.md)
