---
name: align-paper-translation
description: 翻译论文或指定章节，生成连贯译文、可改的双语对照稿和能定位到句段的术语记录。
metadata:
  author: GPT-6.2Astra
---

# 按原文逐段翻译

先完整翻译题目指定的范围，按论文自己的标题、段落、图表题注和编号保留结构。给读者一份可以连续阅读的译文。遇到「respectively」、代词、否定、条件、上下限时，弄清每个修饰语指向哪个对象。术语有两种含义时分别记录使用位置，例如测量仪器中的 level 和水文报告中的 level。

按材料出现顺序指定 scope，每个元素写 source，可用 first、last 限定页内行或段。给每组填写 segments（文件名和原定位的有序对）与 target（实际译句的数组）。跨页续句可以合并，长句可以拆开。两组间的原文片段必须无重无漏。glossary 可按组限制术语的适用语境。上限、单位、公式下标、否定、图表与引文编号逐段复读，保留影响含义的不确定处。

## 从本题材料开始

打开 /input/case.json 和 task.md，按题目指定的材料、语言、范围与交付字段完成本例。附件多时，可用 python3 scripts/casework.py index --input /input --work /app/work 建索引。下列示例展示接口；实际使用时换成实际材料目录和根据材料撰写的 plan.json。

```sh
python3 scripts/parallel_edition.py sample/sources sample/plan.json /tmp/parallel-edition-example
```

translation.txt 是连续译文。parallel.html 将同一语义组并排显示，alignment.json 保存段号、术语和数量差异。安装 python-docx 后还会生成可编辑的 parallel.docx。

进入 /app/output 的成品沿用原 case_id 及 output_contract 的字段与类型。题目要正文时，将实际正文写入指定字段；题目要附件时给对应文件的有效路径。材料出处、无法判断的部分与局限填在相应位置。

[完整工作流与通用入口](FULL_WORKFLOW.md) · [示例与运行环境](sample/README.md)

作品署名　GPT-6.2Astra
