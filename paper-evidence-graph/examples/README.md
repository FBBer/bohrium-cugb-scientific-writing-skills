# 最小调用示例

从单条自写观测抽取一个方法和一个任务，分别查询支持方向、反向关系与类型，验证回查到原句。命中的第一和第三条查询分别输出 query-01-01 与 query-03-01 的可编辑 SVG、PDF 与 PNG。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/paper-evidence-graph-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
