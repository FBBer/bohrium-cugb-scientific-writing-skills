# 引言与相关工作写作使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

输入计划含 language、sections（各含 title、paragraphs），每个 paragraph 由有序句项构成。句项例 {"id":"I1","role":"gap","text":"仅限所比较工作可推出的空白","condition":"比较边界","evidence":[{"id":"S","quote":"最小原文"}]}。角色为 background、comparison、gap、objective、contribution、scope。comparisons 以同一维度列出各工作的 work、axis、method、condition、observed_result、limit 和 evidence。比较表使用能回查的引文；带数值的结果须见于引文或有可复算的推导。缺依据的比较行留在审计文件，供作者补证后使用。

从具体任务和技术约束导入，按可比的问题/方法分组，每组说明共同点、差异和取舍。对照方法不是综述文章自己的实验，注意区分谁提出、谁引用。各论文的数值只有在数据集、划分、指标、预算相容时才能直接比较。引用写在实际受支持的句末，优先使用题目提供的著者和文献键，补充材料只在授权且可核对时使用。

将空白从比较矩阵的覆盖范围推导；“给定文献尚未报告某场景”优于声称整个领域从未做过。在贡献句描述本文做了哪项具体工作、评估的场景及正文证据，计划中的实验用计划语气。用 status=inference、reason 说明作者判断；避免为成文补造题名、DOI、领先性、成功表现或创新排序。

```sh
python3 "$S/scripts/compose.py" introduction /app/work/sources.json /app/work/intro-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

每项研究贡献对应具体工作、适用条件与原文位置，逐行记录在 contribution-evidence.tsv。

派生数值使用 derivation 记录计算。operation 可取 sum、difference、mean、ratio、percent_of 或 percent_change。inputs 依次列两个带原文锚点 id、数值 value 和单位 unit 的数，变化百分比按（新值−基线）/基线计算。复杂推导随稿给出公式和原始数据，另行复算。

需要更换同一量纲的 SI 单位时，用 `derivation.operation=convert_unit`，在 `inputs` 中仅填写所引原值、单位和锚点。例如材料给出 12 kPa，写为 12000 Pa 时填写原值 12、单位 kPa 与真实来源。复合单位和温标换算另附计算。

将每个研究空白连回前文比较，将每个贡献连回本文的方法、结果或图表。输出真正可独立阅读的引言和相关工作正文、比较矩阵、论断—引文对应表及未决信息。表中的技术说明留给核验者，正文保持连贯。

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。
