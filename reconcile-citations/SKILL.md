---
name: reconcile-citations
description: 校验稿件引文与书目、保守去重、按首次出现重排编号并输出可编辑 CSL JSON 和逐处审计。
---

# 参考文献与引用管理

从原稿与原始文献库逐条对应引用。合并重复条目要有 DOI 或一致的书目信息，同名不同版分开。保留原稿中的公式、代码、引用页码、附录与未能确定的文献标记。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/citations.py" /input/library.json /input/manuscript.md /app/output
```

命令接受 CSL JSON、BibTeX 或 RIS 等原库。数字引用与原书目对应；Pandoc 或 LaTeX 文献键按键绑定。交付改后正文、同步的引用库和原句对照。

正文用作者和年份引用时，可识别叙述式、括号内合引及原库给定的年份后缀。同姓同年有多个候选时，在引用记录里列出候选书目。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
