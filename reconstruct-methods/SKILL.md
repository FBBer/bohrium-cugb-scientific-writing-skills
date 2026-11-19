---
name: reconstruct-methods
description: 把配置、代码、日志和论文转为可复核的方法实验章节，协调配置冲突并记录复现所需设置。
---

# 方法与实验章节写作

列明材料来源、实验身份、运行时间与阶段。区分默认配置、提交的有效配置、一次实际运行的覆盖值，以及文章中汇总的设置。按 run_id、版本、数据划分和实验组对齐，多个实验不同取值通常不构成冲突。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

settings.py 对 JSON、YAML、CSV、配置和日志列出同名参数的候选差异，输出值、文件和位置。不同 run、不同作用域分开判定。对同一实验存在不一致时，查匹配实际运行的命令参数和日志，保留旧值、实际值和判据；材料不足时并列，标“需作者确认”。不将随机种子等同独立重复，不将训练规模推作测试样本数。

写有逻辑先后的步骤，各含输入、操作、输出和判定条件。分开说明数据来源与版本、预处理与泄漏控制、样本单位及划分、训练/验证/测试、基线版本和计算预算、评价指标、重复与汇总口径。复现清单只用实际给出的命令/环境，示意命令标明需填项。为每个条件说明失效的具体场景。对无日志证明的步骤区分“拟采用”和“实际执行”。

plan 含 language、sections，分节的 paragraphs 是有序句项数组的数组。每项有 id、role、text、evidence=[{"id":"S","quote":"原文"}]。角色为 procedure、data、split、parameter、evaluation、baseline、environment、repetition、limitation。另给 parameters=[{"name":"参数","value":"实际值","unit":"单位或无量纲","scope":"运行/阶段","status":"reported","evidence":[...]}]；冲突项列两个来源及 resolution，未报告给原因。记录给出参数值但缺单位时，保留数值，将 unit 留空并设 unit_status 为 unreported。“无量纲”须能回指材料中的定义，或在 unit_derivation 逐项写明量纲如何相消并附来源。reproduction 对象记录版本、环境、命令、数据、种子、划分、可复做步骤及缺口。

```sh
python3 "$S/scripts/settings.py" /input /app/work/settings.json
python3 "$S/scripts/compose.py" methods /app/work/sources.json /app/work/methods-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

派生数值使用 derivation 记录计算。operation 可取 sum、difference、mean、ratio、percent_of 或 percent_change。inputs 依次列两个带原文锚点 id、数值 value 和单位 unit 的数，变化百分比按（新值−基线）/基线计算。复杂推导随稿给出公式和原始数据，另行复算。

## 交付与复核

核对正文、参数表和运行记录中的数值、单位与归属，核查百分数的分母。对不需要或缺失的统计量注明该判断的依据。交付 methods.md、parameters.json、reproduction.json 与论断—证据表，按给定案例输出契约填入提交结果。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 阅读版式

研究步骤写入正文，参数、单位和取值依据在同一张表中对齐。设置有冲突时并列条件，报告不确定性时保留原材料的表述。白底黑字，以留白区分内容。来源、单位和影响理解的限定信息使用可读字号。过程记录另存。

需要阅读页时，运行 `python3 "$S/scripts/view.py" 主成果路径 阅读页.html`，将“主成果路径”替换为实际生成的 `methods.md` 路径。离线页面可在浏览器打开。正式交付仍使用题目指定的文件、字段和模板。

## 独立运行环境

结构化 YAML 解析可用 python3 -m pip install PyYAML，本地实测 6.0.3。纯文本键值、JSON 和 CSV 使用 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/reconstruct-methods-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
