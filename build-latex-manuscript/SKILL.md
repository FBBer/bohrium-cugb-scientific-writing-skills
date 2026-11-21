---
name: build-latex-manuscript
description: 在实际模板上修复和编译可编辑的 LaTeX 稿件，检查公式、引用、表格、日志和 PDF。
---

# LaTeX 写作与编译

在作者实际模板中修改并编译稿件。保留公式、单位、引用键、图表和必要附件。查看新生成的 PDF 对应页，确认题注、栏宽与公式编号。

材料较多时，运行 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 建立原文索引，`find` 可按词和文件查位置。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/build.py" /app/work/project auto /app/output/latex-build
```

已知主稿就用相对路径替换 auto。多文件项目会采用经过验证的 TeX root 声明；出现两个独立主稿时按本题指定文件选择。交付 source/、新编译的 PDF 和实际日志。

编译失败时，build.json 的 source_diagnostics 给出报错的实际文件、行号和原句。project_inputs 列出本次编译实际打开的稿件与附件。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
