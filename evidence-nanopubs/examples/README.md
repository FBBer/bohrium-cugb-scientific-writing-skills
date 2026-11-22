# 最小调用示例

把一条自写传感器结论拆为带遮挡条件、极性与出处的断言，导出四个 TriG 命名图。伪造引句的副本应进入未决清单。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/evidence-nanopubs-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。

## 从 TriG 找回原句

```sh
python3 examples/demo.py run
python3 scripts/resolve_quote.py run/output/nanopubs.trig run/work/sources.json
```

第二条命令需要 RDFLib，可用 python3 -m pip install rdflib 安装。输出列出文件、段落、字符起止和带上下文的原句。可用 --publication 指定一条断言的完整 IRI。位置从该版本对应的文本段开头按 Unicode 码点计数，右端开区间。命令同时核对来源段落的摘要和引句上下文。

TriG 中的两个定位器采用 [W3C Web Annotation](https://www.w3.org/TR/annotation-model/#selectors) 的 TextQuoteSelector 和 TextPositionSelector。
