---
name: evidence-nanopubs
description: 科研断言更正谱。将档案中的更正及被更正版本连接为有向修订链，两版都有独立标识。
---

# Nanopublication

## 科研断言更正谱

先按案例要求读原始材料，写出完整的目标产物。将档案中的更正及被更正版本连接为有向修订链，两版都有独立标识。

把实际段落、表格或实验记录的准确原句写入 plan.json。每条 evidence 包含 source、quote，可用 loc 区分重复引文。索引列出可用的文件名与位置。按本题原始材料另写正文或译文，字段格式可看 [示例计划](examples/edition/plan.json)。

```sh
python3 scripts/run_edition.py examples/edition/materials edition-out --plan examples/edition/plan.json
```

实际案例中令 S=/skills/weekly-skill。可先运行 `python3 "$S/scripts/run_edition.py" /input /app/work/edition-index --index`，再将材料目录、输出目录和计划路径换成当次实际路径。只有材料明确说明修订时才建立修订关系；标识应可区分版本。 正文交付沿用任务指定体裁，来源与限制写入要求的字段。

结果目录内的 `edition-report.json` 列出实际生成的文件和需要补充的原始材料。基于原始 case.json 的 output_contract 填写正式 result.json，并把题目要求的可编辑文件及预览放在 /app/output。


## 用观测原句发布断言

断言里的 0.7 cm 可回到原句。改写为 7 mm 仍指同一读数，若写成 7 cm，工具会将它留在待核对记录里。直接观测用原文数值和单位核对，推断另记所用依据。

```sh
python3 scripts/nanopubs.py examples/gauge-source.json examples/gauge-claim.json observations
```

以真实结论段、表格或图注为单位定位。每条断言只表达一种关系，用独立的主体、关系、对象、极性、样本与范围描述它。并列结果可拆分，共用证据应保留同一出处；一个不能单独核验的因果链不得拆成较强的断言。

## 材料与出处

从 `/input/case.json` 和 `task.md` 确定交付内容及格式。用下列命令给附件建立索引，按文件名、页码或行号找原文。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

## 处理实际材料

claims.json 含 claims 数组，单项字段为 id、subject、predicate、object、statement、scope、polarity（positive/negative/uncertain）、evidence_type（direct/inference/reported-by-others）以及 evidence=[{"id":"S","quote":"最小充分原文"}]。推断还需 reason，保留替代解释。若材料给出出处，papers 按索引中 source 的完整值建键，记录 title、identifier、creator、date、hasVersion。publication 仅填写实际知道的本次产物作者、时间或版本，论文作者属于论文来源。

先用相邻上下文确定谁在什么条件下做了什么测量。证据跨度可跨两处，各写一个定位，另保留完整上下文；不能只引“显著”二字。结果缺少单位或方向时降低确定性。互相冲突的论文分别建断言，各保留实验范围；无法建证据的条目写入待核验清单。

脚本检验引文后形成 Head、Assertion、Provenance、PublicationInfo 四个具名图，限定命题保留极性和条件，稳定 ID 包含声明及其位置/证据。发布者与原论文作者分开。输出 assertions.json 和 nanopubs.trig。规范依据 https://nanopub.net/guidelines/working_draft/ 和 https://www.w3.org/TR/trig/ 。

```sh
python3 "$S/scripts/nanopubs.py" /app/work/sources.json /app/work/claims.json /app/output
```

## 交付与复核

重新解析 TriG（可用 rdflib.Dataset().parse(path, format="trig")），每条断言恰有一个 head 指向其三部分，来源图指回 assertion，本次出版图以 nanopub 为主语。逐句比对引文能否支持关系、方向与范围，检查去重和缺失元数据。按契约交付原子断言、图文件和不确定记录。

成稿放在 /app/output，沿用 case.json 中的 case_id 和 output_contract，按 task.md 命名。原文出处及待核对事项写在相应字段。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 独立运行环境

生成 TriG 使用 Python 标准库。在独立环境可用 python3 -m pip install rdflib 安装独立 RDF 解析器，本地验证版本为 7.6.0。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。依赖版本见示例说明。

## 示例

从本目录运行 `python3 examples/demo.py /tmp/evidence-nanopubs-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。

要从断言跳回原文，用 scripts/resolve_quote.py 读取导出的 TriG 和来源索引。引文同时保留文献版本、段落位置、字符区间及前后文。遇到重复句子，在 evidence 中给出 start 或相邻的 prefix、suffix。原文里的推测语气随断言保留。
