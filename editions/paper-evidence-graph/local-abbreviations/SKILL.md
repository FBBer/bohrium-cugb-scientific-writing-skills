---
name: paper-evidence-graph
description: 把跨文献实体与有向关系整理为可查询知识图谱，按每篇文章自己的定义消解重复缩写。
metadata:
  author: GPT-6.2Astra
---

# 同名缩写的证据图

读取问题和各篇文献，列出带类型的实体。definitions 中每个短名和全称都要在该文的引句中出现。edges 用原文出现的词给出起点、终点、关系措辞、条件、极性和证据。跨篇出现相同缩写时只使用该文自己的定义；同一文内有两个解释时保留候选、暂缓建边。题目给的全称可直接做查询入口。按问题说明哪些关系有依据，并列出原句。

## 使用本题材料

读取 /input/case.json、task.md 和列出的附件。把示例命令中的输入换成本题实际文件。将主结果按场景指定的字段和文件名写入 /app/output，保留原 case_id、来源和不确定项。完整的通用处理入口见 [FULL_WORKFLOW.md](FULL_WORKFLOW.md)。

```sh
python3 scripts/abbreviations.py sample/sources sample/plan.json /tmp/abbreviation-graph
```

graph.html 可读查询，graph.json 可查定义原句与歧义，graph.graphml 可编辑。示例的两处 MS 各自表示监测站和镜面传感器，两条边各自回到原报告。

[打开示例成品](sample/preview/graph.html)。sample/ 使用自拟材料。文本处理需要 Python 3.9 或以上；Word、PDF、Excel 的可选依赖和通用工作流见随附说明。

作品署名　GPT-6.2Astra
