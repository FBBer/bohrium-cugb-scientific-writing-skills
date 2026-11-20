---
name: reconcile-citations
description: 校验稿件引文与书目、保守去重、按首次出现重排编号并输出可编辑 CSL JSON 和逐处审计。
---

# 参考文献与引用管理

识别输入书目格式、正文样式、引文种类、目标规范和可用证据。区别参考文献序号、数学下标或区间、图表编号以及标题中的数字。先保存原件，重排始终基于同一版原始稿。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。Excel 实验表按工作表名和单元格定位。数字保留存储值，百分号等格式另列；公式、已有缓存值分别记录，未缓存的公式需要用原工作簿重算。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

脚本接受 CSL JSON、RIS、带百分号标签的 EndNote 文本；BibTeX/BibLaTeX 用 Pandoc 读取。labels 是 {"7":"原始书目键"} 的实际映射；只有原始清单本来从 1 连续编号且顺序一致才可省略。将 Word 正文、脚注、图表题注、附录依阅读顺序提取并记录偏移，然后回写至实际文档；手写简单转换不能替代保留具有域代码的原件。程序会跳过数学、代码和 Markdown 链接。稿内有文末书目时，正文、附录和书目一起重排。遇到缺条目、重号或无法对应的旧引文，保留整稿原编号并列出具体位置。没有数字引文的稿件保持原有书目。文内数字形式有歧义时，在工作副本先标明哪些位置是引文，审计中保留决定。

规范化 DOI 的前缀和大小写；有标点冲突时与原 DOI 元数据比对。无相同标识符时，只有题名、作者序列、年份和类型吻合才能自动合并。数据库记录与期刊最终版、预印本与最终版、不同年份或双语题名须人工确认，并保留版本关系。核对 DOI、作者顺序、年份、卷期、页码/文章号及更正记录。每条书目的 metadata_status 分列核心字段缺项与外部核验，只有实际查过数据库并留下来源、日期，才能记录为已核验。程序离线运行时 external_verification 为 not_performed；题名吻合不足以证明正文结论。

为需要支持的每个论断找最小句段，列支持、部分支持、矛盾、无从判断，附论文定位/原句。综述转述原始结果应注明层级。重复引用映射同一编号；多引范围按目标规范压缩；孤立正文标记、文末未引条目和多余元数据分别报告。著者—年份、上标、期刊 CSL 或 GB/T 等按任务口径排版，需保留原路径和样式版本，可用 Pandoc --citeproc --csl 已提供的样式生成。

```sh
python3 "$S/scripts/citations.py" /app/work/refs.json /app/work/manuscript.md /app/output --labels /app/work/original-labels.json
```

## 交付与复核

citation-audit.json 给出每处引文所在原句、该句及标记在原稿中的字符位置、原键和新编号。用首次出现顺序重算一次编号；核对新标签、文末清单、图表与附录，区分遗漏、引文不支持和元数据未核实。保留原键/新编号对照、合并依据、可导入的书目及可编辑修订稿。用案例的字段和要求的目标格式交付。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 阅读版式

在同一行列出原稿句子、原编号和新编号，编号按列对齐。按首次引用顺序另排书目；原始键和冲突证据保留在引文记录。白底黑字，以留白区分内容。来源、单位和影响理解的限定信息使用可读字号。过程记录另存。

需要阅读页时，运行 `python3 "$S/scripts/view.py" 主成果路径 阅读页.html`，将“主成果路径”替换为实际生成的 `citation-audit.json` 路径。离线页面可在浏览器打开。正式交付仍使用题目指定的文件、字段和模板。

## 独立运行环境

JSON、RIS 和带标签的 EndNote 导入使用 Python 标准库。BibTeX 导入需要 Pandoc，本地实测版本 3.10.1；可安装系统提供的 pandoc 包，并用 pandoc --version 核对。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/reconcile-citations-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
