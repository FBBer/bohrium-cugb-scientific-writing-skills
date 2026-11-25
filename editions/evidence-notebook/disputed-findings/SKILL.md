---
name: evidence-notebook
description: 按论文结构记录发现及其证据，再判断两篇文献的相反结论是否出自相同条件。
metadata:
  author: GPT-6.2Astra
---

# 文献之间的分歧

先沿论文自身章节写出研究问题、材料、方法、发现和局限。每条发现以 note 表述，evidence 逐字定位。比较前统一同一科学问题的命名，scope 分填材料、条件、结局指标和测量方法；缺项留空。结果方向按原文填 increases、decreases、unchanged 或 inconclusive。若有不同方法、载荷或样本，不直接宣布结果冲突；同向或异向均保留两边引文。单篇材料可直接交付章节笔记。

## 使用本题材料

读取 /input/case.json、task.md 和列出的附件。把示例命令中的输入换成本题实际文件。将主结果按场景指定的字段和文件名写入 /app/output，保留原 case_id、来源和不确定项。完整的通用处理入口见 [FULL_WORKFLOW.md](FULL_WORKFLOW.md)。

```sh
python3 scripts/disputes.py sample/sources sample/plan.json /tmp/disputed-findings
```

notebook.html 逐项列出两篇材料和条件，notes.md 可继续编辑，notebook.json 含可比较的条件与证据。三篇示例中只有两篇低载荷研究构成同条件分歧。

sample/ 使用自拟材料。文本处理需要 Python 3.9 或以上；Word、PDF、Excel 的可选依赖和通用工作流见随附说明。

作品署名　GPT-6.2Astra
