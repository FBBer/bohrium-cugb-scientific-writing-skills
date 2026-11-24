---
name: ground-introduction
description: 在共同条件下写相关工作。将来自不同论文的证据按同一比较维度对齐，导出带出处的引言正文和方法比较表。
---

# 引言与相关工作写作

## 在共同条件下写相关工作

先按案例要求读原始材料，写出完整的目标产物。将来自不同论文的证据按同一比较维度对齐，导出带出处的引言正文和方法比较表。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。材料或指标不可比的差异用文字说明，宣传式概括应删去。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 同一段中逐句核对引文

一段里有引文的 4 cm 观测可以入稿，邻句缺少来源时单列出来。原文只写遮阴与降温相关，不能据此写成遮阴导致降温。introduction.md 保留可入稿文字，claim-sources.tsv 列出每句的出处。

```sh
python3 scripts/manuscript.py examples/water-level/papers examples/water-level/draft.md introduction-out --own our.txt --language en
```

## 从普通文稿整理引文和贡献

先根据原文写四段，分别交代背景、同一问题下的既有做法、这些研究留下的具体缺口及本文贡献。每行写一个或几个有关联的论断，在相应从句末放 Markdown 脚注 `[^key]`。文末的脚注定义给出 `材料相对路径 | 原句`。同一句在文献中出现多次时，在路径后加 `#位置`，位置取自原文索引。用 `--own` 指明本文的记录，其余材料作为参考文献。下面的短文为自拟示例。

```sh
python3 scripts/manuscript.py examples/synthesis/papers examples/synthesis/draft.md intro-output --own our-log.txt --bibliography examples/synthesis/references.json --language en --strict
```

`introduction.md` 可直接放进稿件，参考文献按首次出现顺序排列。`claim-sources.tsv` 保留每个从句的出处与原句，`related-work.tsv` 汇总已有工作和空白，`contributions.tsv` 单列本文证据。找不到引文、归错研究或扩大限定范围的行留在 `manuscript-sources.json` 供作者修改。同一测量值若涉及不同文献，分别在各自的从句后引证。自动核对涵盖直接数量、来源和范围；没有独立元数据时保留文件名。作者最终核对转述含义。材料、文稿和输出分别存放。

把研究背景、相关方法、具体空白和本文贡献写成可直接入稿的段落。给每个可核验的主张就近配上原引文，两篇研究的条件和结果分别绑定。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/compose.py" introduction /app/work/sources.json /app/work/intro-plan.json /app/output
```

写作计划按章节、段落、句子组织，工作间的同维度比较另列 comparisons。每个空白回扣已比较的文献，每个贡献回扣本文的实际工作。输出正文、比较矩阵及论断出处。

比较不同研究时，rows 可按论文编号和章节提取原文。同名章节属于哪篇文献，会随引文一起返回。

交付 Word 稿时，在 compose.py 命令末尾加 `--word --preview`。introduction.docx 的每个有依据的论断可跳到文末所引原句，另有同版 PDF。按论文要求保留正文原有的作者年份、引文键或序号。Word 需要 python-docx，PDF 另需 LibreOffice。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
