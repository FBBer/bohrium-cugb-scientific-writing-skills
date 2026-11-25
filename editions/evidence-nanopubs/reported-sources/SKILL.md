---
name: evidence-nanopubs
description: 区分作者亲自观测的结果和作者转述的结果，生成四命名图 TriG 与逐条出处。
metadata:
  author: GPT-6.2Astra
---

# 追溯二手断言的出处

区分作者亲自观测的结果和作者转述的结果，生成四命名图 TriG 与逐条出处。

读取 /input/case.json 和 task.md，按其指定的结构、文件名和语言交付作品。完整处理方式、原始材料索引和其他交付格式见 [完整工作流](FULL_WORKFLOW.md)。

将原文和 claims.json 放在同一目录。每条记录给出 file、line、quote 和 kind。转引还要填写 cited。四张命名图分开保存断言、出处、发布信息和图间关系，provenance.json 能回到原文行。

运行示例

    python3 scripts/attribution.py sample result

[示例结果](sample/preview/)

作品署名　GPT-6.2Astra
