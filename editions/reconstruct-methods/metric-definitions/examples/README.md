# 最小调用示例

比较同一采集过程的默认 20 ms 和运行日志的实际 15 ms，记录两处来源和采用实际配置的理由。未给出的随机种子需保留为缺口。

从作品根目录运行以下命令，目标目录应为本次示例专用目录。

```sh
python3 examples/demo.py /tmp/reconstruct-methods-example
```

脚本现场建立合成输入，写入 input/，处理记录写入 work/，示例主结果写入 output/result.json。源码内含对预期行为的断言，任何一项不满足都会返回错误。此示例与正式评测材料独立。
