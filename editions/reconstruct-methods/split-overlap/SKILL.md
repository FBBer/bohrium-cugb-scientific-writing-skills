---
name: reconstruct-methods
description: 从样本清单重建实验章节，统计独立组别，并列出跨集合组和重复样本。
metadata:
  author: GPT-6.2Astra
---

# 从数据清单重建实验划分

从样本清单重建实验章节，统计独立组别，并列出跨集合组和重复样本。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

输入 samples.csv，用 sample 表示观测编号、group 表示板材或受试者等实验单位、split 表示训练或评估集合。生成的实验段落和逐组明细可直接对照，重复观测保留原始行号。

运行示例

    python3 scripts/splits.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
