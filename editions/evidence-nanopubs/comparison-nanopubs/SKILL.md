---
name: evidence-nanopubs
description: 将论文中的独立断言拆为四个 RDF 具名图，并为可比条件下的成对观测编码原文、方向、单位和出处。
metadata:
  author: GPT-6.2Astra
---

# 把成对观测发布为 Nanopublication

先按题目抽出有科学含义、可分别核验的原子断言，保留极性、样本、条件和原文的确定程度。建立断言、出处、出版信息和连接它们的 Head。普通定性陈述、负结果、推断、文献转述都可按完整工作流中的 claims 接口表达。论文作者是原材料作者，作品署名仅指整理工具。

文中确有两个读数可比较时，各自指定组名、原始数值、单位和逐字引文，另外给出限定两组的条件出处与稿件版本。若整篇确实只研究一种条件，可在核对方法段后使用 single_scope_document。脚本先换算到同一单位，再计算 comparison 减 reference；不给推测、区间、约数或不相容的量纲编造精确差值。以直接观测的关系命名，避免从数值差推断因果或统计显著性。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成实际材料目录和根据材料撰写的 plan.json。

```sh
python3 scripts/comparison_nano.py sample/sources sample/plan.json /tmp/comparison-nanopubs-example
```

comparisons.trig 可被独立 RDF 解析器打开。每个断言的引用可追到原句、位置、版本和原文件指纹。comparisons.json 和比较表便于复核哪一组是参照。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
