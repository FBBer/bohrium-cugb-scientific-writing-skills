---
name: ground-introduction
description: 从逐字可追溯的背景、比较范围和本研究记录组成引言，防止将有限文献外推成普遍结论。
metadata:
  author: GPT-6.2Astra
---

# 给研究空白划定范围

从逐字可追溯的背景、比较范围和本研究记录组成引言，防止将有限文献外推成普遍结论。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

plan.json 按背景、比较、空白与贡献给出可入稿句子和材料行号。空白要写明正在比较的研究范围，属于本文的贡献要连接本文记录。introduction.md 含正文和引文表，claim-map.json 含每句的依据。

运行示例

    python3 scripts/gap.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
