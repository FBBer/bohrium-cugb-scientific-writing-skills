# 最小调用示例

生成两页双栏 PDF，交错写入左右栏文本，另放重复页眉。输出应先读完左栏，再读右栏；两页页眉保存在 marginalia。PDF 用标准库生成。解析需原环境的 PyMuPDF 或 Poppler。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/pdf-reading-order-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
