---
name: reconstruct-methods
description: 实验样本流转表。从每阶段的纳入、排除和原因计算留存数，生成方法正文和可编辑流转表。
---

# 方法与实验章节写作

## 实验样本流转表

先按案例要求读原始材料，写出完整的目标产物。从每阶段的纳入、排除和原因计算留存数，生成方法正文和可编辑流转表。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。阶段可能重叠；是否为下一阶段分母需由材料判断。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 按实验批次找参数

日志里的 R1 先记 15 ms，后记 20 ms。两条记录在 within_run_conflicts 中并列，带原文件与行号。R2 的 25 ms 单独归入 R2。CSV 的种子和嵌套配置中的增益也保留各自的运行编号。

```sh
python3 scripts/settings.py examples/field-runs settings.json
```

列明材料来源、实验身份、运行时间与阶段。区分默认配置、提交的有效配置、一次实际运行的覆盖值，以及文章中汇总的设置。按 run_id、版本、数据划分和实验组对齐，多个实验不同取值通常不构成冲突。

## 材料与出处

从 `/input/case.json` 和 `task.md` 确定交付内容及格式。用下列命令给附件建立索引，按文件名、页码或行号找原文。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

## 处理实际材料

settings.py 对 JSON、YAML、CSV、配置和日志列出同名参数的候选差异，输出值、文件和位置。不同 run、不同作用域分开判定。对同一实验存在不一致时，查匹配实际运行的命令参数和日志，保留旧值、实际值和判据；材料不足时并列，标“需作者确认”。不将随机种子等同独立重复，不将训练规模推作测试样本数。

写有逻辑先后的步骤，各含输入、操作、输出和判定条件。分开说明数据来源与版本、预处理与泄漏控制、样本单位及划分、训练/验证/测试、基线版本和计算预算、评价指标、重复与汇总口径。复现清单只用实际给出的命令/环境，示意命令标明需填项。为每个条件说明失效的具体场景。对无日志证明的步骤区分“拟采用”和“实际执行”。

plan 含 language、sections，分节的 paragraphs 是有序句项数组的数组。每项有 id、role、text、evidence=[{"id":"S","quote":"原文"}]。角色为 procedure、data、split、parameter、evaluation、baseline、environment、repetition、limitation。另给 parameters=[{"name":"参数","value":"实际值","unit":"单位或无量纲","scope":"运行/阶段","status":"reported","evidence":[...]}]；冲突项列两个来源及 resolution，未报告给原因。reproduction 对象记录版本、环境、命令、数据、种子、划分、可复做步骤及缺口。

```sh
python3 "$S/scripts/settings.py" /input /app/work/settings.json
python3 "$S/scripts/compose.py" methods /app/work/sources.json /app/work/methods-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

## 交付与复核

核对正文、参数表和运行记录中的数值、单位与归属，核查百分数的分母。对不需要或缺失的统计量注明该判断的依据。交付 methods.md、parameters.json、reproduction.json 与论断—证据表，按给定案例输出契约填入提交结果。

成稿放在 /app/output，沿用 case.json 中的 case_id 和 output_contract，按 task.md 命名。原文出处及待核对事项写在相应字段。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

结构化 YAML 解析可用 python3 -m pip install PyYAML，本地实测 6.0.3。纯文本键值、JSON 和 CSV 使用 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。依赖版本见示例说明。

## 示例

从本目录运行 `python3 examples/demo.py /tmp/reconstruct-methods-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
