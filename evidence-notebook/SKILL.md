---
name: evidence-notebook
description: 沿论文真实结构建立含研究条件、发现和局限的笔记卡片、可检索主题索引及逐条证据映射。
---

# 结构化阅读笔记

沿论文实际章节写出研究问题、数据、方法、结果及限制。每个关键数值带研究对象、条件和原文位置。将作者的解释、读者的推断和原文观察分别标出。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/compose.py" notes /app/work/sources.json /app/work/notes-plan.json /app/output
```

notes.md 可直接阅读，paper-cards.json 按论文保留事实、解释、局限和有出处的争议，topic-index.json 用于查找主题。比值的两条原始读数若来自表格，需要分别引用两格与各自的列头。

从实验表做笔记时，可按研究对象和条件定位同一条观测。rows 返回该格读数、单位列头与原行位置。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
