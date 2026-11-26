---
name: ground-introduction
description: 根据实际论文、研究底稿和图表记录撰写可编辑的引言与相关工作。适用于按方法比较文献、限定研究空白、落实本文贡献或逐句核对引用。
---

# 逐句落实来源的引言稿

先在 Skill 所在目录运行 `python3 run.py`。它会读取本次案例与真实附件，将原文按文件及位置整理到 `/app/work/source-cards.json`。下面的起草和再次运行由调用本 Skill 的 Agent 完成。

## 从材料到正文

1. 阅读 `/input/task.md`、`/input/case.json` 及来源卡。确定语言、读者、篇幅、引用格式与具体问题，辨别本人研究底稿和前人文献。对图、表、PDF 扫描页直接看原件。卡片列不出某项时，查原材料再引用。
2. 在 `/app/work/draft.json` 写一份只属于本案例的稿。`paragraphs` 按论证顺序排列，每段有 `role` 和 `claims`。每句包含已经写好的 `text` 与 `evidence`，后者为 `{"file":"材料路径","quote":"原文片段"}` 的数组。重复引文加 `loc` 和 `start`（对应来源段内从 0 开始的字符位置）。英文或中文都可写，`language` 分别用 `en`、`zh`。正文用目标语言，引文保留原文。
3. 用 `background` 写一个具体问题，`comparison` 按研究条件或方法写可比较的结论，`gap` 说明是哪几篇论文的什么边界，`contribution` 接住这个缺口。单篇路线描述也可用 `related`。将目标论文或实验记录的文件名写进 `own`。只需改某部分时用 `required_roles` 列出任务实际要求的部分，已有草稿作为独立文件保留。
4. 跨论文比较句附 `comparison`，格式见示例。`kind: contrast` 表示比较适用条件，`kind: rank` 表示性能排序。`by_source` 逐篇给原文中出现的 `metric`、`condition`，可添 `time`、`dataset` 等。不同数据、单位或时间先说明取舍。具体数字各自成句，放在对应文献旁。
5. 空白句附 `gap`。`scope` 是该句明确写出的范围，`papers` 列出该判断引用的文件。`kind: limitation` 需要原文明确给出限制；`kind: disagreement` 还要给 `comparison` 证明研究条件可比。文献没有谈到的问题可写成作者提出的问题，不能据此声称全领域无人研究。贡献中的图号、数值、比较方向和已完成的实验与本研究原件逐项核对。
6. `works` 可选。每个来源对应原件中的完整书目文字，或 `{"parts":["作者","年份","题名","出处"],"sources":["论文","书目文件"]}`。各组成项均须能在指定材料中定位。缺项保留材料标识并在 `uncertainty` 中说明。脚本默认顺序编码。遇到题面指定著者年份等其它体例，用已核验元数据调整成稿、参考文献和相应交付字段。保留每条论断的原文映射。
7. 运行 `python3 run.py` 完成写作。打开 `/app/output/introduction.md` 通读每段，`claims.json` 核对原句与资料，`comparisons.json` 核对比较条件。`claims.json` 中的 `review` 和 `bibliography_review` 在正文之外；有证据就改正并重跑，缺材料则在最终不确定项写明。Word 交稿加 `--word`，可编辑文档和由 LibreOffice 渲染的 PDF 放在同一目录。修订原稿加 `--original materials/draft.md`，可得逐行改动。
8. 按原案例 `output_contract` 交付 `/app/output/result.json`。自定义章节、目标期刊格式或其他指定字段由 Agent 按刚生成的稿件写成 `/app/work/fields.json`，重跑 `python3 run.py --fields /app/work/fields.json`。不合原字段类型时看 `/app/work/contract-review.json`，完整稿与证据仍在输出目录。

## 最小示例

~~~sh
python3 examples/make_sample.py /tmp/tide/input /tmp/tide/work/draft.json
python3 run.py --input /tmp/tide/input --work /tmp/tide/work --output /tmp/tide/out --word
~~~

这份虚构案例对比实地岸边和水槽两组观测，再用本次渡河测量回应采样缺口。示例输出有四段可编辑正文。`claims.json` 中能定位到每一次引用的具体字符，正文不会夹入审稿意见。完整可改的输入结构见样例生成器。

核心流程用 Python 3.9+ 标准库。PDF 材料可用 PyMuPDF 或 Poppler。Word 导出另需 `python3 -m pip install python-docx`、LibreOffice 的 `soffice` 和目标语言字体。半成稿仅作中间保存，调用 Agent 负责完成要求的篇幅、逻辑和语境转述，逐字引用匹配本身不能证明句义正确。

作者模型 GPT-6.2Astra。公开源码位置见同目录 `GITHUB_URL.txt`。
