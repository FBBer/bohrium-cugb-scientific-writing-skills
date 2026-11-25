---
name: build-latex-manuscript
description: 顺着主稿的输入顺序定位标签与引用，将重复标签、失效引用定位到原文件行，并保留可编译的示例 PDF。
metadata:
  author: GPT-6.2Astra
---

# 多文件稿件中的公式引用

顺着主稿的输入顺序定位标签与引用，将重复标签、失效引用定位到原文件行，并保留可编译的示例 PDF。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

从 main.tex 的输入顺序检查子文件，支持前向引用、跨文件标签、重复标签和注释。references.json 定位定义与使用位置，references.md 便于逐条修稿。复杂宏由完整工作流中的实际编译处理。示例全文与编译后的 main.pdf 均随作品提供。

运行示例

    python3 scripts/labels.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
