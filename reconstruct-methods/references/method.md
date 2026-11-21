# 方法与实验章节写作使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

settings.py 对 JSON、YAML、CSV、配置和日志列出同名参数的候选差异，输出值、文件和位置。不同 run、不同作用域分开判定。对同一实验存在不一致时，查匹配实际运行的命令参数和日志，保留旧值、实际值和判据；材料不足时并列，标“需作者确认”。不将随机种子等同独立重复，不将训练规模推作测试样本数。

写有逻辑先后的步骤，各含输入、操作、输出和判定条件。分开说明数据来源与版本、预处理与泄漏控制、样本单位及划分、训练/验证/测试、基线版本和计算预算、评价指标、重复与汇总口径。复现清单只用实际给出的命令/环境，示意命令标明需填项。为每个条件说明失效的具体场景。对无日志证明的步骤区分“拟采用”和“实际执行”。

plan 含 language、sections，分节的 paragraphs 是有序句项数组的数组。每项有 id、role、text、evidence=[{"id":"S","quote":"原文"}]。角色为 procedure、data、split、parameter、evaluation、baseline、environment、repetition、limitation。另给 parameters=[{"name":"参数","value":"实际值","unit":"单位或无量纲","scope":"运行/阶段","status":"reported","evidence":[...]}]；冲突项列两个来源及 resolution，未报告给原因。参数值只能由能在原附件定位的引文或推导支持；找不到原句时，该参数保留名称和作用域，数值留空。记录给出参数值但缺单位时，保留数值，将 unit 留空并设 unit_status 为 unreported。“无量纲”须能回指材料中的定义，或在 unit_derivation 逐项写明量纲如何相消并附来源。reproduction 对象记录版本、环境、命令、数据、种子、划分、可复做步骤及缺口。

```sh
python3 "$S/scripts/settings.py" /input /app/work/settings.json
python3 "$S/scripts/compose.py" methods /app/work/sources.json /app/work/methods-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

派生数值使用 derivation 记录计算。operation 可取 sum、difference、mean、ratio、percent_of 或 percent_change。inputs 依次列两个带原文锚点 id、数值 value 和单位 unit 的数，变化百分比按（新值−基线）/基线计算。复杂推导随稿给出公式和原始数据，另行复算。

需要更换同一量纲的 SI 单位时，用 `derivation.operation=convert_unit`，在 `inputs` 中仅填写所引原值、单位和锚点。例如材料给出 12 kPa，写为 12000 Pa 时填写原值 12、单位 kPa 与真实来源。复合单位和温标换算另附计算。

核对正文、参数表和运行记录中的数值、单位与归属，核查百分数的分母。对不需要或缺失的统计量注明该判断的依据。交付 methods.md、parameters.json、reproduction.json 与论断—证据表，按给定案例输出契约填入提交结果。

结构化 YAML 解析可用 python3 -m pip install PyYAML，本地实测 6.0.3。纯文本键值、JSON 和 CSV 使用 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

当参数的 evidence 含配置和实测日志时，selected_evidence 值是其中一项完整的 {id,quote}；最终值要能在选定的那一条得到。做比值、均值与单位换算时可分别引用 Word 或 Excel 数据格及对应列头，把表示单位的原表头也列入 evidence。
