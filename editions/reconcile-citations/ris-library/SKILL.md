---
name: reconcile-citations
description: 可导入的 RIS 文献库。从有出处的作者、题名、年份及 DOI 导出 RIS，可在文献管理器继续编辑。
---

# 参考文献与引用管理

## 可导入的 RIS 文献库

先按案例要求读原始材料，写出完整的目标产物。从有出处的作者、题名、年份及 DOI 导出 RIS，可在文献管理器继续编辑。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。按原作保留作者顺序，未知年份留空。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 区分同名的不同版本

同名、同年、同一作者的两条记录若各有一个 DOI，会保留两版。第三条记录缺 DOI 时，两种可能都列出来，文内引用仍指向作者选的那条。示例书目和 DOI 为自拟记录。

```sh
python3 scripts/citations.py examples/gauge-versions.json examples/gauge-citations.md references-out
```

从原稿与原始文献库逐条对应引用。合并重复条目要有 DOI 或一致的书目信息，同名不同版分开。保留原稿中的公式、代码、引用页码、附录与未能确定的文献标记。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/citations.py" /input/library.json /input/manuscript.md /app/output
```

命令接受 CSL JSON、BibTeX 或 RIS 等原库。数字引用与原书目对应；Pandoc 或 LaTeX 文献键按键绑定。交付改后正文、同步的引用库和原句对照。

正文用作者和年份引用时，可识别叙述式、括号内合引及原库给定的年份后缀。同姓同年有多个候选时，在引用记录里列出候选书目。

作者已经选定来源、需要将引用插到原句时，先用 place.py 以段落中的原句定位，再将输出交给 citations.py 排序。位置与库中条目的写法见方法说明。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
