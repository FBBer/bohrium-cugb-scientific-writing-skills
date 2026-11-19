---
name: evidence-nanopubs
description: 将有出处的科研结论拆为可单独验证的断言，生成带证据、来源与出版信息的四命名图 TriG。
---

# Nanopublication

以真实结论段、表格或图注为单位定位。每条断言只表达一种关系，用独立的主体、关系、对象、极性、样本与范围描述它。并列结果可拆分，共用证据应保留同一出处；一个不能单独核验的因果链不得拆成较强的断言。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

claims.json 含 claims 数组，单项字段为 id、subject、predicate、object、statement、scope、polarity（positive/negative/uncertain）、evidence_type（direct/inference/reported-by-others）以及 evidence=[{"id":"S","quote":"最小充分原文"}]。推断还需 reason，保留替代解释。source_modality 可填引文内出现的原词，如“可能”，claim_strength 可选 reported、tentative 或 inferred。比较性断言把两个对象和方向一并回指原句。每个断言保留来源的语气；同一引文若另有带限定的子句，缩小引文范围，或在 modality_context 中明确该词修饰的对象。若材料给出出处，papers 按索引中 source 的完整值建键，记录 title、identifier、creator、date、hasVersion。publication 仅填写实际知道的本次产物作者、时间、版本或许可，论文作者属于论文来源。

先用相邻上下文确定谁在什么条件下做了什么测量。证据跨度可跨两处，各写一个定位，另保留完整上下文；不能只引“显著”二字。结果缺少单位或方向时降低确定性。互相冲突的论文分别建断言，各保留实验范围；无法建证据的条目写入待核验清单。

脚本检验引文后形成 Head、Assertion、Provenance、PublicationInfo 四个具名图，限定命题保留极性和条件，稳定 ID 包含声明及其位置/证据。发布者与原论文作者分开。输出 assertions.json 和 nanopubs.trig。规范依据 https://nanopub.net/guidelines/working_draft/ 和 https://www.w3.org/TR/trig/ 。

```sh
python3 "$S/scripts/nanopubs.py" /app/work/sources.json /app/work/claims.json /app/output
```

## 交付与复核

重新解析 TriG（可用 rdflib.Dataset().parse(path, format="trig")），每条断言恰有一个 head 指向其三部分，来源图指回 assertion，本次出版图以 nanopub 为主语。逐句比对引文能否支持关系、方向与范围，检查去重和缺失元数据。按契约交付原子断言、图文件和不确定记录。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 阅读版式

以适用条件为小节标题，突出断言原句。保留否定、推测和转引限定，逐条关联证据。命名图与版本标识放在该条出处内。白底黑字，以留白区分内容。来源、单位和影响理解的限定信息使用可读字号。过程记录另存。

需要阅读页时，运行 `python3 "$S/scripts/view.py" 主成果路径 阅读页.html`，将“主成果路径”替换为实际生成的 `assertions.json` 路径。离线页面可在浏览器打开。正式交付仍使用题目指定的文件、字段和模板。

## 独立运行环境

生成 TriG 使用 Python 标准库。在独立环境可用 python3 -m pip install rdflib 安装独立 RDF 解析器，本地验证版本为 7.6.0。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/evidence-nanopubs-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
