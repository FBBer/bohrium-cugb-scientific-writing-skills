---
name: build-latex-manuscript
description: 在实际 LaTeX 模板中排版和编译论文，用稳定数据键将正文的测量值、误差与表格同步，交付可重新编译的源码和 PDF。
metadata:
  author: GPT-6.2Astra
---

# 用同一份数据生成论文正文和表格

读稿件、任务说明、模板与给定事实，找到主文件和子文件。依稿件要求保留作者、符号、编号、引文、章节和排版。在测量表上标识稳定键，给出值、单位、可选误差和显示精度，始终保留 CSV 的原精度与真实零。正文用 \ObsValue{键} 引同一记录，表格用 \ObsTableRows。主文件在使用它们前输入生成的 .tex，表格保留原有题注、标签与浮动体位置。遇到多种统计误差，在实际表头或题注中说明具体含义，勿自行补充。

有现成模板时先修复使其能在原编译环境复现。缺资料则交付能确认的可编辑部分、编译日志和准确的错误位置。没有这种数据表时按普通 LaTeX 稿要求使用 scripts/build.py（见完整工作流），继续修公式断行、引文收敛、模板类或版心。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成编辑后的论文工程和根据材料撰写的 plan.json。

```sh
python3 scripts/data_manuscript.py sample/sources sample/plan.json /tmp/data-to-manuscript-example
```

manuscript.pdf 和 source/ 是可以阅读与继续编辑的成品。measurement-sources.json 将正文键连回 CSV 行和原精度，build.json、compile.log 列出引擎与实际诊断。用交付的 source/ 再编译一次，查看有变动的正文与表格页。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
