# Nanopublication使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

claims.json 含 claims 数组，单项字段为 id、subject、predicate、object、statement、scope、polarity（positive/negative/uncertain）、evidence_type（direct/inference/reported-by-others）以及 evidence=[{"id":"S","quote":"最小充分原文"}]。推断还需 reason，保留替代解释。source_modality 可填引文内出现的原词，如“可能”，claim_strength 可选 reported、tentative 或 inferred。比较性断言把两个对象和方向一并回指原句。每个断言保留来源的语气；同一引文若另有带限定的子句，缩小引文范围，或在 modality_context 中明确该词修饰的对象。若材料给出出处，papers 按索引中 source 的完整值建键，记录 title、identifier、creator、date、hasVersion。publication 仅填写实际知道的本次产物作者、时间、版本或许可，论文作者属于论文来源。

先用相邻上下文确定谁在什么条件下做了什么测量。证据跨度可跨两处，各写一个定位，另保留完整上下文；不能只引“显著”二字。结果缺少单位或方向时降低确定性。互相冲突的论文分别建断言，各保留实验范围；无法建证据的条目写入待核验清单。

脚本检验引文后形成 Head、Assertion、Provenance、PublicationInfo 四个具名图，限定命题保留极性和条件，稳定 ID 包含声明及其位置/证据。发布者与原论文作者分开。输出 assertions.json 和 nanopubs.trig。规范依据 https://nanopub.net/guidelines/working_draft/ 和 https://www.w3.org/TR/trig/ 。

```sh
python3 "$S/scripts/nanopubs.py" /app/work/sources.json /app/work/claims.json /app/output
```

重新解析 TriG（可用 rdflib.Dataset().parse(path, format="trig")），每条断言恰有一个 head 指向其三部分，来源图指回 assertion，本次出版图以 nanopub 为主语。逐句比对引文能否支持关系、方向与范围，检查去重和缺失元数据。按契约交付原子断言、图文件和不确定记录。

生成 TriG 使用 Python 标准库。在独立环境可用 python3 -m pip install rdflib 安装独立 RDF 解析器，本地验证版本为 7.6.0。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

每项命题的 RDF 描述含 rdf:subject、rdf:predicate、rdf:object 和限定信息。仅直接、肯定、已报告的观察在相应断言图中另有该关系三元组；否定、推断和可能性按限定命题查询。提供标识时采用来源所用的绝对 IRI。未给受控标识时，程序按出处与语境建立本地标识。

直接证据写成被动语态时，将 by 后的施事放在关系起点。支持常见英文动词的明显反向、否定与可能性识别。引文为复句、关系需跨段推断时，保留必要的完整语境与推理依据。
