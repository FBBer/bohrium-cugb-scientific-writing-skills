---
name: reconstruct-methods
description: 把配置、代码、日志和论文转为可复核的方法实验章节，协调配置冲突并记录复现所需设置。
---

# 方法与实验章节写作

按执行顺序重建可复现的方法与实验章节。核对数据、划分、对照、真实运行参数、评测条件及限制。区分预设值与日志中实际使用的值。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。 以下路径中的材料名按本次输入替换。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/settings.py" /input /app/work/settings.json
python3 "$S/scripts/compose.py" methods /app/work/sources.json /app/work/methods-plan.json /app/output
```

遇到配置与实际日志冲突时，在参数里同时引两者，用 selected_evidence 明确哪一条记录支持最终采用的值。正文、参数表与复现步骤均可独立使用。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
