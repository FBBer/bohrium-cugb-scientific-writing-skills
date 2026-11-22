# 最小调用示例

从带表格、带标签公式和交叉引用的 LaTeX 源码实际编译出 PDF。脚本检查源文件、PDF 文件头和第二遍引用；需可用的 pdflatex。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/build-latex-manuscript-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
