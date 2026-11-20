---
name: ground-introduction
description: 用限定来源组织研究背景、比较既有工作、推导有范围的空白，并把贡献逐项对应本文证据。
---

# 引言与相关工作写作

先分清本研究的稿件、图表、实验记录与外部工作。给每个研究问题建立比较轴，如任务、对象、数据/场景、方法假设、评价口径和局限。阅读本研究实证范围之后再写贡献句。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。Excel 实验表按工作表名和单元格定位。数字保留存储值，百分号等格式另列；公式、已有缓存值分别记录，未缓存的公式需要用原工作簿重算。写作时同时引用数值单元格及同一连续数据列的单位表头，可保留原量纲。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

输入计划含 language、sections（各含 title、paragraphs），每个 paragraph 由有序句项构成。句项例 {"id":"I1","role":"gap","text":"仅限所比较工作可推出的空白","condition":"比较边界","evidence":[{"id":"S","quote":"最小原文"}]}。角色为 background、comparison、gap、objective、contribution、scope。comparisons 以同一维度列出各工作的 work、axis、method、condition、observed_result、limit 和 evidence。比较表使用能回查的引文；带数值的结果须见于引文或有可复算的推导。缺依据的比较行留在审计文件，供作者补证后使用。

从具体任务和技术约束导入，按可比的问题/方法分组，每组说明共同点、差异和取舍。对照方法不是综述文章自己的实验，注意区分谁提出、谁引用。各论文的数值只有在数据集、划分、指标、预算相容时才能直接比较。引用写在实际受支持的句末，优先使用题目提供的著者和文献键，补充材料只在授权且可核对时使用。

将空白从比较矩阵的覆盖范围推导；“给定文献尚未报告某场景”优于声称整个领域从未做过。在贡献句描述本文做了哪项具体工作、评估的场景及正文证据，计划中的实验用计划语气。用 status=inference、reason 说明作者判断；避免为成文补造题名、DOI、领先性、成功表现或创新排序。

```sh
python3 "$S/scripts/compose.py" introduction /app/work/sources.json /app/work/intro-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

每项研究贡献对应具体工作、适用条件与原文位置，逐行记录在 contribution-evidence.tsv。

派生数值使用 derivation 记录计算。operation 可取 sum、difference、mean、ratio、percent_of 或 percent_change。inputs 依次列两个带原文锚点 id、数值 value 和单位 unit 的数，变化百分比按（新值−基线）/基线计算。复杂推导随稿给出公式和原始数据，另行复算。

## 交付与复核

将每个研究空白连回前文比较，将每个贡献连回本文的方法、结果或图表。输出真正可独立阅读的引言和相关工作正文、比较矩阵、论断—引文对应表及未决信息。表中的技术说明留给核验者，正文保持连贯。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 阅读版式

引言和相关工作各自成段，先呈现可直接使用的正文。逐篇比较用短列名，列出研究、条件与范围，并保留论断的出处。白底黑字，以留白区分内容。来源、单位和影响理解的限定信息使用可读字号。过程记录另存。

需要阅读页时，运行 `python3 "$S/scripts/view.py" 主成果路径 阅读页.html`，将“主成果路径”替换为实际生成的 `introduction.md` 路径。离线页面可在浏览器打开。正式交付仍使用题目指定的文件、字段和模板。

## 独立运行环境

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/ground-introduction-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
