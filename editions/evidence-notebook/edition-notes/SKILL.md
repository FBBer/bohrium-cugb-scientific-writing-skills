---
name: evidence-notebook
description: 按论文原有论证顺序整理研究问题、方法、发现与局限，定位每条证据，并在修订稿上找回原段或重写笔记。
metadata:
  author: GPT-6.2Astra
---

# 随论文修订的阅读笔记

逐节阅读材料，用论文实际的章节名作笔记的骨架。先写能独立读懂的章节摘要，说明作者研究了什么、用何种资料、在什么条件下得到什么结果。每个重要判断紧接可核对的段落、图表或单元格。作者的观测、解释与读者推论分开措辞；实验没有涵盖的范围写在对应发现旁。

单篇论文直接给出 sections，每条笔记的 before 指向该篇，省略 current_source。需要接续修订稿时，current_source 指新文件，程序用旧段落全文及其最近的 Markdown 章标题匹配。只移动了位置的原句会获得新定位。同句多处出现、语境所属章节有变或数字改过时，旧判断留作历史记录。亲自读过新句子后，可给 replacement 填入 note 和 evidence，写出新版本实际支持的解释。PDF 的章标题需由阅读者按版面核对。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成实际材料目录和根据材料撰写的 plan.json。

```sh
python3 scripts/edition_notes.py sample/sources sample/plan.json /tmp/edition-notes-example
```

notebook.html 将当前结论摆在原章节下。展开“上版记载”可以看到数值为何改变；notebook.md 可在普通笔记软件里继续写，notes.json 保留两版的文件、行与原句。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
