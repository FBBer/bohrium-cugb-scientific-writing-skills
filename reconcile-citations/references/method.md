# 参考文献与引用管理使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

脚本接受 CSL JSON、RIS、带百分号标签的 EndNote 文本；BibTeX/BibLaTeX 用 Pandoc 读取。labels 是 {"7":"原始书目键"} 的实际映射；原稿带有编号书目时，可用 DOI 或唯一题名匹配文献库，编号可以不连续。无原始书目且库序不明时请提供实际编号映射。将 Word 正文、脚注、图表题注、附录依阅读顺序提取并记录偏移，然后回写至实际文档；手写简单转换不能替代保留具有域代码的原件。程序会跳过数学、代码和 Markdown 链接。稿内有文末书目时，正文、附录和书目一起重排。遇到缺条目、重号或无法对应的旧引文，保留整稿原编号并列出具体位置。没有数字引文的稿件保持原有书目。文内数字形式有歧义时，在工作副本先标明哪些位置是引文，审计中保留决定。

规范化 DOI 的前缀和大小写；有标点冲突时与原 DOI 元数据比对。无相同标识符时，只有题名、作者序列、年份和类型吻合才能自动合并。数据库记录与期刊最终版、预印本与最终版、不同年份或双语题名须人工确认，并保留版本关系。核对 DOI、作者顺序、年份、卷期、页码/文章号及更正记录。每条书目的 metadata_status 分列核心字段缺项与外部核验，只有实际查过数据库并留下来源、日期，才能记录为已核验。程序离线运行时 external_verification 为 not_performed；题名吻合不足以证明正文结论。

为需要支持的每个论断找最小句段，列支持、部分支持、矛盾、无从判断，附论文定位/原句。综述转述原始结果应注明层级。重复引用映射同一编号；多引范围按目标规范压缩；孤立正文标记、文末未引条目和多余元数据分别报告。著者—年份、上标、期刊 CSL 或 GB/T 等按任务口径排版，需保留原路径和样式版本，可用 Pandoc --citeproc --csl 已提供的样式生成。

```sh
python3 "$S/scripts/citations.py" /app/work/refs.json /app/work/manuscript.md /app/output --labels /app/work/original-labels.json
```

citation-audit.json 给出每处引文所在原句、该句及标记在原稿中的字符位置、原键和新编号。用首次出现顺序重算一次编号；核对新标签、文末清单、图表与附录，区分遗漏、引文不支持和元数据未核实。保留原键/新编号对照、合并依据、可导入的书目及可编辑修订稿。用案例的字段和要求的目标格式交付。

JSON、RIS 和带标签的 EndNote 导入使用 Python 标准库。BibTeX 导入需要 Pandoc，本地实测版本 3.10.1；可安装系统提供的 pandoc 包，并用 pandoc --version 核对。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

对于 [@article-key, p. 12; -@other] 与 LaTeX 文献命令，保留页码、引文命令及顺序。确属同一条记录的旧键转到规范键，无法匹配的键保持原文并列出位置。混合使用数字与键时，保留原稿的数字标记并分别对应文献。代码和行内数学中的示例标记保留。

原库给出的年份后缀可写入 year-suffix，例如 a。作者与年份匹配后，原句和起止位置写入 citation-audit.json。数字与作者年份混合出现时保留原有标记。有多个同姓同年候选时，查原文题名或 DOI 再决定。

## 引用插在原句

将作者选定的原句和对应文献库 ID 写入 placements.json。例如稿件出现 “The two series were measured independently.”，材料中确实有支持这句的条目 keller，可写 `{"placements":[{"quote":"The two series were measured independently.","records":["keller"],"style":"pandoc"}]}`。重复的句子用紧邻的 prefix、suffix 或原稿中从零计的字符位置 start 分辨。

```sh
python3 "$S/scripts/place.py" library.json manuscript.md placements.json work/cited
python3 "$S/scripts/citations.py" library.json work/cited/manuscript-cited.md output
```

LaTeX 稿选 style 为 latex。一句合引的所有条目放进同一 records 数组。已有原论文时，加上 `--sources work/sources.json`；对应条目写在 support 数组内，每项含 record（所选书目 ID）、id（所引来源段 ID）、quote（原句）。placements.json 的结果列出插入前的字符范围及书目，来源原句可以逐字回查。工具根据作者选择放置引文；措辞强度、研究人群与结论之间的支持程度要根据论文核定。
