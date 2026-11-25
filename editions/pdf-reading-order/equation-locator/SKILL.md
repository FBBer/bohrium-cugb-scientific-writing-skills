---
name: pdf-reading-order
description: 解析论文的段落、表格和公式，把正文里的公式编号连到实际印刷页。
metadata:
  author: GPT-6.2Astra
---

# 公式与引文逐页定位

从任务指定范围提取正文、表格和公式。编号公式要一起保留符号、上下标、编号和依赖上下文。正文引用式（2）时先找同号展示公式，再核对该页的原图。索引记录物理页、原句、矩形坐标和局部 PNG。重复编号列出各页，未定位的引文仍保留。扫描页先看原页，必要时使用环境可用的 OCR 核对；完整解析与交付见 FULL_WORKFLOW.md。

## 使用本题材料

读取 /input/case.json、task.md 和列出的附件。把示例命令中的输入换成本题实际文件。将主结果按场景指定的字段和文件名写入 /app/output，保留原 case_id、来源和不确定项。完整的通用处理入口见 [FULL_WORKFLOW.md](FULL_WORKFLOW.md)。

```sh
python3 sample/make_pdf.py /tmp/plate.pdf
python3 scripts/equations.py /tmp/plate.pdf /tmp/plate-formulas
```

equations.html 可连续阅读引句与公式原图；equations.json 中的 displays 和 references 指回原页。示例的正文在第一页引用式（2），公式位于第二页。运行需 Python 3.9+ 与 PyMuPDF，可用 python3 -m pip install pymupdf 安装。

[打开示例成品](sample/preview/equations.html)。sample/ 使用自拟材料。文本处理需要 Python 3.9 或以上；Word、PDF、Excel 的可选依赖和通用工作流见随附说明。

作品署名　GPT-6.2Astra
