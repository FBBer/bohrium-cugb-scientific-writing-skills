---
name: align-paper-translation
description: 对科研材料制作逐段双语译稿，锁定术语，复核数字、公式、引用和限定语。用于段落级有来源定位的翻译。
---

# 文献翻译

识别源语、目标语、翻译范围、指定写法和文体。先列全篇段落、题注、表头与脚注，在段落身份确定后再翻译。跨页续段合并时记两个页码。无法读取的内容占一条带定位的未译记录。

## 从本次案例开始

读取 /input/case.json、同目录 task.md 和列出的原始附件。若存在 environment/resources.yaml，按其记录使用当前镜像的工具。在工作目录记下输出字段、类型、语言、文件名和原材料位置。用实际材料内容判断领域。此包不依赖其他参赛目录、网络、密钥或个人绝对路径。

```sh
S=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$S/scripts/casework.py" index --input /input --work /app/work
```

sources.json 保存真实文件、位置和逐字摘录。JSON 输入可按 JSON Pointer 回查，PDF 使用物理页号，文本使用行号。除说明和输出契约外，case.json 内嵌的材料也会被索引。检查文件清单中的图片、表格和解析警告，必要时用原生阅读器打开。索引只是定位工具，以原附件为准。

## 执行方法

segments.json 采用 {"segments":[{"id":"p1-s1","location":"p1, Abstract ¶1","text":"原文逐字摘录"}],"glossary":{"source term":{"target":"规定译名","accepted":[],"forbidden":[]}}}。translation.json 是按原顺序排列的 [{"id":"p1-s1","target":"实际译文"}]。例子中的文字只说明字段。按材料中的定义记全称、缩写、同义词和领域义项。译名优先级为用户规定、文内定义、学科惯用译名。多义词写明在哪些段落采用哪种意义，将对应术语应用到相应段组。accepted 可列出作者认可的别称，forbidden 可列出在本义项下禁用的译名。定稿前逐一还原公式、引文等临时标记。

逐段保留论证关系和句子顺序；长段按从句分批再复合。记录跨段指代对象、比较对象、条件、否定作用域、可能性强度和论断主体。标题、图表题注、脚注同样译全。保护数学表达式、单位、区间、显著性符号、图表编号和参考文献。数字保留精度；若任务要求单位换算，附原值、因子和手算核对。

脚本比较逐段有重数的数字/公式/引文、术语、图表类型、ID 集合与顺序。逐条回原文判定术语误报或实错；一个词表对应多个学科含义时分组运行。机器提示无法证明语义相同，需要人工式反译关键句，特别是未显著、不能排除、仅适用于和相关性。

```sh
python3 "$S/scripts/prose.py" translate /app/work/segments.json /app/work/translation.json /app/output --strict
```

负定词数量相同仍可能改变含义。逐句对照否定词实际支配的动作，特别留意“未发生漂移”与“未停止漂移”、“无法排除”与“已经排除”。审计报告含数量或语义待核项时，可加 --strict 使程序返回非零；审定的翻译变体应保留判断依据。

## 交付与复核

输出 bilingual.md、可复用术语表和复核记录，写明每一处纠正、不能确定的读法及句号/页码。段落覆盖率以实际源段清单为分母；译段重复或空缺必须定位。按原契约补齐 JSON，禁止以摘要代替译文。

把可编辑成果写入 /app/output。正文使用适合目标读者的科研表达，直接给出译文、论证、参数或结论。每个结果沿用原 case_id 和 output_contract 的字段、类型与层级。输出文件名遵循 task.md。来源差异、缺项的具体原因和运行状态写入契约指定字段或单独的审计文件。Office 文档和图形按要求附可编辑源与实物渲染。

```sh
python3 "$S/scripts/casework.py" check --case /input/case.json --result /app/output/result.json
```

## 阅读版式

原文与译文按段同行对齐，保留公式、图号、数值和限定词。段落位置可集中展开，窄屏按原文、译文的次序阅读。白底黑字，以留白区分内容。来源、单位和影响理解的限定信息使用可读字号。过程记录另存。

需要阅读页时，运行 `python3 "$S/scripts/view.py" 主成果路径 阅读页.html`，将“主成果路径”替换为实际生成的 `bilingual.md` 路径。离线页面可在浏览器打开。正式交付仍使用题目指定的文件、字段和模板。

## 独立运行环境

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

## 可复用的最小示例

从本目录运行 `python3 examples/demo.py /tmp/align-paper-translation-example`。示例使用自写的小样本，实际运行结果保存在指定目录，输入和预期现象见 [示例说明](examples/README.md)。发行版本 1.0，运行环境为 Python 3.9 或以上。可在作品仓库相应目录的 Issues 中附匿名化最小复现、实际输出和依赖版本反馈问题。
