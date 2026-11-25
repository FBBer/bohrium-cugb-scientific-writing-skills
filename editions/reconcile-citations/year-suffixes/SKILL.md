---
name: reconcile-citations
description: 为同作者同年作品统一生成后缀，改写正文引文并给出对应的文献表和缺项。
metadata:
  author: GPT-6.2Astra
---

# 同作者同年份的引文消歧

为同作者同年作品统一生成后缀，改写正文引文并给出对应的文献表和缺项。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

将 Markdown 正文与书目放在同一目录。引文形式如 [@z; @a]，书目给出 id、author、year 和 title。同作者同年按题名分配 a、b 等后缀，多处引用共用同一编号。未找到的文献键完整保留。

运行示例

    python3 scripts/year_suffix.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
