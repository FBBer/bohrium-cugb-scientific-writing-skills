---
name: align-paper-translation
description: 对科研材料制作逐段双语译稿，锁定术语，复核数字、公式、引用和限定语。用于段落级有来源定位的翻译。
---

# 文献翻译

按原文顺序完成双语译稿，覆盖指定段落、标题、图注和表头。保留公式、单位、否定、比较对象和适用条件。术语表写清原词、选定译法和首次出现处。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。只交文本时可省略 Word 和 PDF 两个选项。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
python3 "$S/scripts/segments.py" /app/work/sources.json paper.docx /app/work/segments.json
python3 "$S/scripts/prose.py" translate /app/work/segments.json /app/work/translation.json /app/output --word --preview
```

segments.json 的 segments 含 id、location、text；translation.json 是逐段的 id、target 数组。--word 额外输出可编辑的双语对照表，原文位置在左栏。

原稿为 Word 时，先从索引生成 segments.json。翻译完成后给 prose.py 加上 --original-docx /input/paper.docx，可让两栏保留可编辑分式。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
