---
name: evidence-notebook
description: 沿论文真实结构建立含研究条件、发现和局限的笔记卡片、可检索主题索引及逐条证据映射。
---

# 结构化阅读笔记

## 从论文到章节笔记

先读题目说明，确定要整理的论文和重点。把材料目录与输出目录分开。通读时用论文原有小节，比较时用跨论文矩阵；每条发现保留所用条件、原文位置和对应版本。Markdown、分节纯文本、Word 标题和有文字层的 PDF 可以直接处理。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/notebook.py" /input /app/work/notebook --paper 实际论文.pdf
```

打开 notebook.html，按原章节阅读，点段落位置看带高亮的原句。PDF 可从该处打开原页。notes.md 用于继续写作，study-matrix.tsv 可导入表格，reading-cards.json 和 comparison.tsv 保留字段、引句及位置。要优先摘录含有指定关键词的原句，可以多次使用 --focus。--per-role 限制跨论文矩阵每栏的条数，独立小节仍保留代表性内容。

同一读数可能出现在不同地点。查找时带上章节或条件，保留不同小节的重复观察。给定明确的随文表格，可用 --table '论文文件=表格文件' 连接 CSV 或 TSV。看数值时要带上原行、列头与单位，重复观测按测次区分。示例使用自拟的水尺记录。

```sh
python3 scripts/notebook.py examples/river river-notes --table 'river-stage.md=readings.tsv'
python3 scripts/recall.py river-notes search '0.7' --section 上游浅滩 --role finding
python3 scripts/recall.py river-notes table readings.tsv --where 测站=深槽 --where 水情=退水 --where 测次=2 --field '偏差 (cm)'
```

把找到的结果写进题目要求的字段。recall 的 --originals 参数可同时核对原文件版本。图像扫描页、文本层损坏、公式或原作者未交代的因果关系，需要回到相应原页阅读。只有能指回原文的内容才作为论文结论。

## 撰写自己的解释与跨论文比较

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
