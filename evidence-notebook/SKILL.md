---
name: evidence-notebook
description: 按原章节整理文献笔记，保留每项发现的适用条件，可查原句、页码和随文表格。
---

# 结构化阅读笔记

## 从论文到章节笔记

把论文放在材料目录，另选目录存笔记。可以读 Markdown、分节纯文本、有标题的 Word 文档和有文字层的 PDF。下面的命令整理一篇论文。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/notebook.py" /input /app/work/notebook --paper 实际论文.pdf
```

打开 notebook.html，按论文章节读。属于同一原段的连续摘句排在一起，点行号或页码可以看出处。有明确适用条件的结果也会列在页首，点表中的句子就能回到正文。页底有论文、Markdown 笔记和多篇论文的对照表。要优先摘录某个主题，可用 --focus 指定关键词。--per-role 控制对照表每栏的条数。

制作多篇笔记可重复使用 --paper。coverage.json 同时记录整批和单篇的阅读范围。整批状态 complete 表示所选论文均可摘录，partial 表示部分文件或页有读取限制，unreadable 表示没有提取到正文。扫描页和加密文件在阅读页列出实际文件和可用页码，其他论文仍能继续整理。若全为不可读材料，命令退出码为 2，仍写出阅读范围与原文入口。文件名或附表声明写错时，可以修正参数后重跑。

示例中，上游和下游的偏差都是 0.7 cm。查上游就指定“上游浅滩”，查某次复测就带上测站、水情和测次。用 --table 指明哪张 CSV 或 TSV 表属于哪篇论文。

```sh
python3 scripts/notebook.py examples/river river-notes --table 'river-stage.md=readings.tsv'
python3 scripts/recall.py river-notes search '0.7' --section 上游浅滩 --role finding
python3 scripts/recall.py river-notes table readings.tsv --where 测站=深槽 --where 水情=退水 --where 测次=2 --field '偏差 (cm)'
```

把找到的结果写进题目要求的字段。recall 的 --originals 参数可同时核对原文件版本。comparison.tsv 的末四列记录本条锚点和关联条件的锚点、原句、位置，三个条件字段均为 JSON 数组。Markdown 与跨论文表也保留了条件关系。读者推断、暂缺的数据以及需要查图或 OCR 的页码应单独说明。

## 撰写自己的解释与跨论文比较

已有自己的摘录提纲时，也可以按提纲成稿。写自己的推断，请注明理由和引用的原句。比较两篇论文时，分别保留各自的研究对象和观测条件。

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
