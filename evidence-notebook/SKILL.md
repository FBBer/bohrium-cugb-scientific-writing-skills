---
name: evidence-notebook
description: 沿论文真实结构建立含研究条件、发现和局限的笔记卡片、可检索主题索引及逐条证据映射。
---

# 结构化阅读笔记

## 从一组论文直接做笔记

把论文放进一个目录，运行下面的命令。可读取有文字层的 PDF、Word、Markdown 和纯文本。示例包含两篇自拟的中英文短文。

```sh
python3 scripts/notebook.py examples/papers reading-notes --focus 漂移 --focus drift
```

先读 `reading-notes/notes.md`，再按编号找到原文。`study-matrix.tsv` 把各篇论文的同类证据并排列在一张表中。`comparison.tsv` 按论文、研究问题、方法、发现、作者解释和局限列出原句；`reading-cards.json` 另存位置和字符范围。只有正文中出现的内容才进入笔记。缺少哪一类原文记在 `uncovered`，原文中的参考文献列表不参与摘录。多材料目录可重复添加 `--paper 相对路径`。`--language en` 使用英文栏目；`--per-role 4` 可增加各栏摘录。输出放在材料目录之外。手写解释或跨论文综合时，用下方的 compose 工作流。

沿论文实际章节写出研究问题、数据、方法、结果及限制。每个关键数值带研究对象、条件和原文位置。将作者的解释、读者的推断和原文观察分别标出。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/compose.py" notes /app/work/sources.json /app/work/notes-plan.json /app/output
```

notes.md 可直接阅读，paper-cards.json 按论文保留事实、解释、局限和有出处的争议，topic-index.json 用于查找主题。比值的两条原始读数若来自表格，需要分别引用两格与各自的列头。

从实验表做笔记时，可按研究对象和条件定位同一条观测。rows 返回该格读数、单位列头与原行位置。

交付可编辑笔记时，在 compose.py 命令末尾加 `--word --preview`。notes.docx 保留作者拟定的章节，每条笔记后面的编号可跳至原句、文件名和原文位置。notes.pdf 由同一 Word 文件生成。Word 需要 python-docx，PDF 另需 LibreOffice。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
