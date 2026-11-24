---
name: build-latex-manuscript
description: 自定义数学符号索引。从定义到正文调用追踪作者指定的 TeX 命令，给出每个出现点和原句。
---

# LaTeX 写作与编译

## 自定义数学符号索引

先按案例要求读原始材料，写出完整的目标产物。从定义到正文调用追踪作者指定的 TeX 命令，给出每个出现点和原句。

按实际材料填写 [示例计划](examples/edition/plan.json) 中需要的词表、命令或输入文件名。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。仅声明关注的数学命令；复杂重定义与展开以实际编译为准。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 编译放在子目录的期刊稿

article/main.tex 引用同目录下的 sections/observations.tex。下面的命令会保留可编辑工程，并在 compiled/manuscript.pdf 生成正文。若根目录和子目录有同名输入，可用 --workdir article 明确选择。

```sh
python3 scripts/build.py examples/gauge-journal article/main.tex compiled
```

盘点主文件、子文件、模板 cls/sty、bib/bst、图表资源、要求的引擎/发行版/字体。先保留原始文件，定位模板真实入口、工作目录和原有编译流程。输入只有 PDF 时，按任务重建可编辑源码，区分能核对和资料缺失的内容。

## 材料与出处

从 `/input/case.json` 和 `task.md` 确定交付内容及格式。用下列命令给附件建立索引，按文件名、页码或行号找原文。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

## 处理实际材料

明确要求的引擎用 --engine pdflatex、xelatex 或 lualatex。脚本以项目根为工作目录，尊重源文件魔术注释与 Unicode 宏包。先运行 latexmk，环境缺少时运行引擎并按 .bcf/.aux 选择 Biber/BibTeX，比较辅助文件直至收敛。每轮保留实际命令、退出码和日志。入口在子目录时，可保留整个模板目录。将外部必需的文件随源码交付。代码不打开 shell escape；若稿件存在外部生成步骤，只处理已提供的源和资源，并明确记录依赖。

按首个实质性错误和对应文件行号修复，每次记录“现象—根因—最小改动—重编结果”。检查缺文件、包冲突、未闭合环境、重复标签、缺字体、未定义文献和引用。保留原数学符号、正斜体、编号、表达含义、图表单元格和小数位，按模板处理题注/图索引/宽表。修复溢出优先断行、对齐和列规格。缺少科学数据时记录缺口。

build 目录产出 source/、manuscript.pdf、build.json、compile.log。PDF 只从当前成功编译复制。打开 log 区分需要再编译的警告与最终未定义引用；打开对应页并检查题注、公式、页边、表头和脚注，保存真实页面预览。用 pdftoppm -f 1 -l 1 -png -r 125 -singlefile manuscript.pdf preview，或使用 PyMuPDF 按相关页渲染。

```sh
python3 "$S/scripts/build.py" /app/work/project main.tex /app/output/latex-build
```

科研图保留原始数据、绘图源码与可编辑矢量文件。中文稿统一使用中文标注，坐标、图例写明量和单位；误差带注明统计含义。流程图以浅色分区，每个虚线分组标明阶段名称，箭头只连接实际依赖。表格在列头标单位、量值按有效精度对齐。按模板实际栏宽查看细线、字号、图例和题注。

## 交付与复核

在干净目录用交付源码二次编译，逐页比较提取文本、页数、公式/表格/引文标记和渲染；PDF 时间戳不作为版面变化依据。把构建和源材料映射写入 result.json 的原契约字段。无法编译时仍交付可编辑源码、准确日志、恢复位置及部分状态。

成稿放在 /app/output，沿用 case.json 中的 case_id 和 output_contract，按 task.md 命名。原文出处及待核对事项写在相应字段。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

本地复核使用 TeX Live 2026 和 latexmk 4.88。独立环境安装与模板匹配的 TeX Live 组件及其 BibTeX/Biber、字体、宏包；用 pdflatex --version 和 latexmk -version 记录实际版本。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。依赖版本见示例说明。

## 示例

从本目录运行 `python3 examples/demo.py /tmp/build-latex-manuscript-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
