---
name: ground-introduction
description: 用限定来源组织研究背景、比较既有工作、推导有范围的空白，并把贡献逐项对应本文证据。
---

# 引言与相关工作写作

把研究背景、相关方法、具体空白和本文贡献写成可直接入稿的段落。给每个可核验的主张就近配上原引文，两篇研究的条件和结果分别绑定。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/compose.py" introduction /app/work/sources.json /app/work/intro-plan.json /app/output
```

写作计划按章节、段落、句子组织，工作间的同维度比较另列 comparisons。每个空白回扣已比较的文献，每个贡献回扣本文的实际工作。输出正文、比较矩阵及论断出处。

比较不同研究时，rows 可按论文编号和章节提取原文。同名章节属于哪篇文献，会随引文一起返回。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
