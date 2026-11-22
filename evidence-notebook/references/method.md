# 结构化阅读笔记使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

工作计划是 {"language":"zh","sections":[{"title":"真实章节名","paragraphs":[[{"id":"N1","role":"finding","text":"该条发现和边界","condition":"成立条件","keywords":["检索词"],"evidence":[{"id":"索引锚点","quote":"逐字证据"}]}]]}]}。合法角色 question、data、method、finding、limitation、definition、context、interpretation。paragraphs 的外层为段落、内层为句子或笔记项。摘要应重述论文实际问题、材料范围、关键条件、主要结果和作者承认的局限。用章节间的依赖解释为何下一部分出现。

把数值与单位、比较对象、评价指标和实验设定绑定；分开写参数与结论、观察与作者解释。对同一结果的正文和图表数值分别取证，有差异就写清各自位置和可疑原因。用一致的索引词串起缩写与同义词；跨论文比较时区分真实可比字段与不可比条件。给每条缺失信息设置 status=unreported 或 uncertain 并说明 reason；推断标 inference、给出依据。

```sh
python3 "$S/scripts/compose.py" notes /app/work/sources.json /app/work/notes-plan.json /app/output --strict
```

在跨文献比较或参数归属句中，为每一对研究主体和条件分别给出 bindings。每项用 id、quote、subject_in_source、condition_in_source 记录同一来源子句里的两个原文片段；把该引文也列入本句 evidence。脚本逐对检查锚点及两个片段能否同时回指该子句。正文翻译过的名称、指代和因果关系仍需逐句对应。

派生数值使用 derivation 记录计算。operation 可取 sum、difference、mean、ratio、percent_of 或 percent_change。inputs 依次列两个带原文锚点 id、数值 value 和单位 unit 的数，变化百分比按（新值−基线）/基线计算。复杂推导随稿给出公式和原始数据，另行复算。

需要更换同一量纲的 SI 单位时，用 `derivation.operation=convert_unit`，在 `inputs` 中仅填写所引原值、单位和锚点。例如材料给出 12 kPa，写为 12000 Pa 时填写原值 12、单位 kPa 与真实来源。复合单位和温标换算另附计算。

检查来源映射中的每一条引文，重点检查主要发现、方法边界以及结论可能失效的条件。paper-cards.json 按论文列出原文事实、解释与局限。作者的解释用 interpretation 角色；读者推断用 inference 状态，并列理由及所据原句。要比较两篇论文，在计划的 comparisons 中填写 left 和 right（两个笔记 ID）、axis、comparability（comparable、conditional 或 not_comparable）和 reason，写清对象、条件、指标或分辨率的差别。交付可读笔记、论文卡片、主题索引和主张溯源表，并在 case 的字段中给出真实卡片和未决项。

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

Word 原生分式按分子和分母线性表达，上下标保留。附注使用自身编号或正文引用段的位置。表内计算时同时引用数值格和其对应列头；跨语言重排同组条件时，bindings 可给 subject_in_text，标明改写后对应的样品。paper-cards.json 的 boundaries 收录有来源的冲突或不确定项。

例如 python3 scripts/casework.py rows --index /app/work/sources.json --source runs.tsv --where sample Chalk --where condition wet --select 'Pressure (kPa)'。用 matched_fields 中的样本和条件、values 中的读数以及 header 列头作出处。把各 id 和 quote 放入该句的 evidence。

需要登记同一行的读数时，可在该句添加 observations。例如 {"source":"runs.tsv","where":{"sample":"Chalk","condition":"wet"},"field":"Pressure (kPa)","value_id":"实际读数的 id"} 是数组中的一项。按数据表的真实字段填写，并在 evidence 中一并列出筛选字段和读数。若同一条件有多次测量，另加观测编号区分。

引用分隔表中的数值格时，正文明确点名的组别须与同一行的样品或条件一致。参数条目中的 scope 采用相同的对应方式。多组比较需分别引用实际测量的各行。

双栏 PDF 首选 PyMuPDF，按栏和跨栏区块整理。没有 PyMuPDF 时，可用 Poppler 的 pdftotext 或 pypdf 提取文本。Word 标题从文档的样式与层级读取。扫描页没有文字层时保留页号，须另做 OCR 或人工核对。索引中的字符位置使用 Unicode 码点，右端不含；PDF 的页为物理页码，B 为页内源区块。近邻条件只在同一小节内绑定；复杂叙述、图表和远距离限定需要沿原文或作者计划核对。CSV/TSV 表格需原始列名唯一，用多个筛选字段仍有多行时保留全部候选。

普通文本、Word 和表格使用 Python 3.9 或更新版本的标准库。PDF 分栏实测使用 PyMuPDF；可用 python3 -m pip install PyMuPDF 安装。阅读页离线可用，和原材料保持相对目录关系即可从笔记打开原件。
