---
name: evidence-notebook
description: 把论文按章节整理成证据笔记，再按同一实验对象配对随文数据，计算差值并交付可继续分析的工作表。
metadata:
  author: GPT-6.2Astra
---

# 原文与配对数据合读

沿用论文自己的章节顺序写阅读笔记。每节抓住研究问题、测量对象、条件、方法、结果及局限中实际出现的内容，同一句结论给出可以回看的证据。作者直接报告的结果和自己从随文数据重新计算的量分开表述。遇到多篇论文或附表时保留材料间的对应关系。

有可比的成对观测时指定数据表、对象键、左右两次观测、数值、单位和筛选条件。对象键须标识同一受试对象或样本，而非仅表示重复编号。脚本在各对象内部统一量纲，算右侧减左侧，以左侧为分母算百分比。只有配齐的对象计入均差；保留零点读数、缺测、真实的零差，以及无法合并的单位。相同期别出现重复读数时回看原实验设计，不擅自挑一条。如果论文只报告独立组总体，直接整理原表和组间边界，使用普通章节笔记流程。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成实际材料目录和根据材料撰写的 plan.json。

```sh
python3 scripts/paired_readings.py sample/sources sample/plan.json /tmp/paired-readings-example
```

notebook.html 收录章节和重算结果，notes.json 可检索每个判断的原句，pairs.tsv 列出两个原始行号、配对差与相对变化。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
