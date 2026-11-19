# 最小调用示例

将两段自写的光学实验描述译为中文，保留 10 ms、引文 [4]、图号和否定关系；对故意把计时数值改错的一份副本再次运行审计。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/align-paper-translation-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
