---
name: align-paper-translation
description: 对科研材料制作逐段双语译稿，锁定术语，复核数字、公式、引用和限定语。用于段落级有来源定位的翻译。
---

# 文献翻译

识别源语、目标语、翻译范围、指定写法和文体。先列全篇段落、题注、表头与脚注，在段落身份确定后再翻译。跨页续段合并时记两个页码。无法读取的内容占一条带定位的未译记录。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。先核查原材料能否支持问题，将明确要求的输出字段、类型、语言和文件名记在工作目录。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

segments.json 采用 {"segments":[{"id":"p1-s1","location":"p1, Abstract ¶1","text":"原文逐字摘录"}],"glossary":{"source term":{"target":"规定译名","accepted":[]}}}。translation.json 是按原顺序排列的 [{"id":"p1-s1","target":"实际译文"}]。例子中的文字只说明字段。按材料中的定义记全称、缩写、同义词和领域义项。译名优先级为用户规定、文内定义、学科惯用译名。多义词写明在哪些段落采用哪种意义，将对应术语应用到相应段组。

逐段保留论证关系和句子顺序；长段按从句分批再复合。记录跨段指代对象、比较对象、条件、否定作用域、可能性强度和论断主体。标题、图表题注、脚注同样译全。保护数学表达式、单位、区间、显著性符号、图表编号和参考文献。数字保留精度；若任务要求单位换算，附原值、因子和手算核对。

脚本比较逐段有重数的数字/公式/引文、术语、图表类型、ID 集合与顺序。逐条回原文判定术语误报或实错；一个词表对应多个学科含义时分组运行。机器提示无法证明语义相同，需要人工式反译关键句，特别是未显著、不能排除、仅适用于和相关性。

```sh
python3 "$S/scripts/prose.py" translate /app/work/segments.json /app/work/translation.json /app/output
```

## 交付与复核

输出 bilingual.md、可复用术语表和复核记录，写明每一处纠正、不能确定的读法及句号/页码。段落覆盖率以实际源段清单为分母；译段重复或空缺必须定位。按原契约补齐 JSON，禁止以摘要代替译文。

先将已完成的真实部分保存到 /app/output，逐轮补齐。将主结果本身写入 /app/output/result.json，保持原 case_id、原 output_contract 的全部字段、类型和层级。原契约禁止额外字段时把审计放在旁文件。明确标记缺材料、原文未报告、证据冲突和工具失败，附已完成范围、证据定位、未决项与实际改动。Office 或图形有要求时同时保留真正可编辑源和渲染预览。最后运行下方契约检查并打开每个必需产物。脚本只查结构，仍需以原文判断主结果。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/align-paper-translation-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
