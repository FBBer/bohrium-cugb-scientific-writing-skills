---
name: paper-evidence-graph
description: 把论文中的实体和有向关系整理成可查询的证据图，回答两种方法在同一条件下共同观测了什么。
metadata:
  author: GPT-6.2Astra
---

# 从两篇论文查共同证据

先从实际问题确定节点类型、可回答的关系和比较条件。为每个实体给出固定 ID、名称、类型、必要的别名。对重复拼写先核对实体类型和实验语境；同一缩写指向多项时使用核准的 ID。给每条有向边填写 from、to、predicate、polarity、scope 和 evidence，surface 填出原文表达关系的措辞。条件在方法段交代时另外填 scope_evidence。

问题指定两个主体、同一种关系和限定条件。分别沿出边查找目标，并要求两条支持证据来自两个文件。正反观察一并保留，列出单独待解释的目标。先用自然语言回答用户问题，随后给出可以回到论文的两句话。其他查询形态（单节点、路径、上下游或多关系）用原有图谱构建和查询流程。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成实际材料目录和根据材料撰写的 plan.json。

```sh
python3 scripts/two_source_join.py sample/sources sample/plan.json /tmp/two-source-join-example
```

answers.html 先显示答案，再列两篇论文的原句。graph.graphml 可在 Gephi 或 yEd 编辑；graph.json 保存别名、方向、冲突和每个答案所用的边。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
