---
name: build-latex-manuscript
description: 在实际模板上修复和编译可编辑的 LaTeX 稿件，检查公式、引用、表格、日志和 PDF。
---

# LaTeX 写作与编译

盘点主文件、子文件、模板 cls/sty、bib/bst、图表资源、要求的引擎/发行版/字体。先保留原始文件，定位模板真实入口、工作目录和原有编译流程。输入只有 PDF 时，按任务重建可编辑源码，区分能核对和资料缺失的内容。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。先核查原材料能否支持问题，将明确要求的输出字段、类型、语言和文件名记在工作目录。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

明确要求的引擎用 --engine pdflatex、xelatex 或 lualatex。脚本以项目根为工作目录，尊重源文件魔术注释与 Unicode 宏包。先运行 latexmk，环境缺少时运行引擎并按 .bcf/.aux 选择 Biber/BibTeX，比较辅助文件直至收敛。每轮保留实际命令、退出码和日志。模板只在带 root/entrypoint 的特定子目录工作时，传那个实际目录为 project，并把相对引用资源一并保留。将外部必需的文件随源码交付。代码不打开 shell escape；若稿件存在外部生成步骤，只处理已提供的源和资源，并明确记录依赖。

按首个实质性错误和对应文件行号修复，每次记录“现象—根因—最小改动—重编结果”。检查缺文件、包冲突、未闭合环境、重复标签、缺字体、未定义文献和引用。保留原数学符号、正斜体、编号、表达含义、图表单元格和小数位，按模板处理题注/图索引/宽表。修复溢出优先断行、对齐和列规格。缺少科学数据时记录缺口。

build 目录产出 source/、manuscript.pdf、build.json、compile.log。PDF 只从当前成功编译复制。打开 log 区分需要再编译的警告与最终未定义引用；打开对应页并检查题注、公式、页边、表头和脚注，保存真实页面预览。用 pdftoppm -f 1 -l 1 -png -r 125 -singlefile manuscript.pdf preview，或使用 PyMuPDF 按相关页渲染。

```sh
python3 "$S/scripts/build.py" /app/work/project main.tex /app/output/latex-build
```

## 交付与复核

在干净目录用交付源码二次编译，逐页比较提取文本、页数、公式/表格/引文标记和渲染；PDF 时间戳不作为版面变化依据。把构建和源材料映射写入 result.json 的原契约字段。无法编译时仍交付可编辑源码、准确日志、恢复位置及部分状态。

先将已完成的真实部分保存到 /app/output，逐轮补齐。将主结果本身写入 /app/output/result.json，保持原 case_id、原 output_contract 的全部字段、类型和层级。原契约禁止额外字段时把审计放在旁文件。明确标记缺材料、原文未报告、证据冲突和工具失败，附已完成范围、证据定位、未决项与实际改动。Office 或图形有要求时同时保留真正可编辑源和渲染预览。最后运行下方契约检查并打开每个必需产物。脚本只查结构，仍需以原文判断主结果。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/build-latex-manuscript-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
