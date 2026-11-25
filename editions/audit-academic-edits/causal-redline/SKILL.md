---
name: audit-academic-edits
description: 逐句比较润色前后的因果措辞、证据强弱和数值，保留可采用的修改和原始全文。
metadata:
  author: GPT-6.2Astra
---

# 保住原研究的论断强度

逐句比较润色前后的因果措辞、证据强弱和数值，保留可采用的修改和原始全文。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

draft.txt 每行一段，edits.json 指明行号、原文和建议。工具逐段生成可读正文、逐条修订与对照稿。数值、因果和不确定性改变的句子保留原稿供作者选择。

运行示例

    python3 scripts/redline.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
