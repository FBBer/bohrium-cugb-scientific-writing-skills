# 最小调用示例

修正两句自写物理测量原稿的主谓一致和分词，保留否定关系、5 mm 与图号。演示对照故意改变单位的稿件。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/audit-academic-edits-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
