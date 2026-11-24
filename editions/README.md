# 地大第一期参赛工具

每个目录含可独立使用的 Skill、运行入口与示例材料。

## 阅读01｜文献文档解析

- [图表题注导航](pdf-reading-order/caption-links)。在正文中找到图表调用，回到对应题注所在的物理页和坐标。
- [印刷页码对照册](pdf-reading-order/printed-folios)。按物理页排列页眉页脚的罗马或阿拉伯页码，并保留 PDF 内嵌页标签。
- [页边重复文字分离](pdf-reading-order/marginalia)。用文字位置和跨页复现率找出运行页眉、页脚，保留每一次出现的位置。
- [脚注往返索引](pdf-reading-order/note-pairs)。按页底位置、字号与脚注标记，把注释和正文中的调用配对。

## 阅读03｜文献翻译

- [科研译文记忆库](align-paper-translation/translation-memory)。从确认的源文、译文生成可交换的 TMX 1.4 译文记忆，另附逐段并排阅读页。
- [数字与界值对照稿](align-paper-translation/quantity-alignment)。按分段比较原译文的数字、误差、界值和顺序，可逐条定位漏译或交换的数值。
- [双语术语用例集](align-paper-translation/term-concordance)。从词表回找全部实际出现的分段，逐一核对译名及上下文。

## 阅读10｜文献总结与结构化笔记

- [按章节找原句](evidence-notebook/passage-finder)。将正文、章节、物理页或行号写入 SQLite 全文索引，附带可离线检索的逐段阅读页。
- [跨论文对照笔记](evidence-notebook/comparison-grid)。沿共同的问题、材料或观测条件对齐多篇论文，在同一格保留原文和出处。
- [文献组会问答卡](evidence-notebook/recall-deck)。将作者提出的研究问题制成先问后答的卡片并输出制表符文件，可以导入复习工具。

## 阅读14｜Nanopublication

- [可引用的四图断言](evidence-nanopubs/quoted-statements)。为每条有出处的关系生成四个 RDF 命名图，导出 N-Quads 与人读断言表。
- [带单位的测量断言](evidence-nanopubs/measured-claims)。在 RDF 断言中保留带类型的数值与单位，并核对两者能否在原文中共同定位。
- [科研断言更正谱](evidence-nanopubs/revision-history)。将档案中的更正及被更正版本连接为有向修订链，两版都有独立标识。

## 阅读15｜文献知识图谱构建

- [逐跳证据路径](paper-evidence-graph/evidence-paths)。查询两个研究实体之间的一条最短有向路径，每一跳可追到原句。
- [单实体关系图册](paper-evidence-graph/local-atlas)。以指定对象为中心列入边、出边和证据，便于从单个材料或方法读起。
- [随时间变化的知识图](paper-evidence-graph/time-slice)。按日期截取当时有效的关系，并单列无日期的关系。

## 写作02｜学术语言润色

- [科学量逐句修订稿](audit-academic-edits/scientific-invariants)。逐词展示改稿，并把数值序列与作者指定的符号、单位和术语对回原句。
- [可选择接受的修订稿](audit-academic-edits/selective-revision)。每项修改可独立接受或保留原句，导出可继续编辑的稿件和编辑决定。
- [术语首次出现校订](audit-academic-edits/abbreviation-order)。按文档行序查每个简称第一次出现和首次定义的位置，方便逐页校订。
- [按段落作用审稿](audit-academic-edits/argument-redline)。将文字按研究问题、方法、结果或边界组织修订，留下逐词差异和编辑理由。

## 写作04｜参考文献与引用管理

- [DOI 与文献版本清单](reconcile-citations/doi-families)。按实际出处中的 DOI 归组，列出相同标识的不同引用键及没有 DOI 的记录。
- [引用回到段落](reconcile-citations/backlink-index)。从 Pandoc 或 LaTeX 引文回到出现它的所有段落，另列漏入书目的键和未引用记录。
- [引用首次出现编号表](reconcile-citations/numbered-crosswalk)。按引文首次出现生成编号和旧键对照，同时导出按序书目用于定稿。
- [可导入的 RIS 文献库](reconcile-citations/ris-library)。从有出处的作者、题名、年份及 DOI 导出 RIS，可在文献管理器继续编辑。

## 写作08｜引言与相关工作写作

- [在共同条件下写相关工作](ground-introduction/matched-comparisons)。将来自不同论文的证据按同一比较维度对齐，导出带出处的引言正文和方法比较表。
- [从空白到本研究贡献](ground-introduction/contribution-chain)。把已有研究的局限与本研究实际产物成对组织，每段正文旁保留两侧的原证据。
- [按技术转折组织引言](ground-introduction/historical-thread)。依据有出处的年份和方法变化组织发展线，保留每一阶段的实际限制。
- [研究适用范围地图](ground-introduction/difference-in-scope)。按数据条件组织文献的已有覆盖与明确缺口，把范围写入可编辑的引言。

## 写作09｜方法与实验章节写作

- [独立样本与复测分层](reconstruct-methods/replicate-hierarchy)。按实验条件分别统计独立观测单位和单位内复测，导出可编辑方法正文。
- [分场次复现实验配置](reconstruct-methods/parameter-overrides)。把共同参数与单场次覆盖项合成可运行配置，每一项保留来源类型和实验标识。
- [实验样本流转表](reconstruct-methods/sample-flow)。从每阶段的纳入、排除和原因计算留存数，生成方法正文和可编辑流转表。
- [评价指标计算稿](reconstruct-methods/metric-definitions)。按已给分子、分母重算评价量，再将计算口径、单位和材料位置写入方法表。

## 写作13｜LaTeX 写作与编译

- [从实验表到可编译长表](build-latex-manuscript/typeset-tables)。从 CSV/TSV 排出带重复表头的 LaTeX 长表，并生成最小可编译预览。
- [跨文件交叉引用图册](build-latex-manuscript/reference-atlas)。在 TeX 源码中追踪标签与引用的文件行号，列出重复、缺失和未引用标签。
- [投稿源文件依赖清单](build-latex-manuscript/asset-manifest)。逐条核对章节、参考文献和插图实际文件，支持相对子目录与常见扩展名。
- [自定义数学符号索引](build-latex-manuscript/notation-register)。从定义到正文调用追踪作者指定的 TeX 命令，给出每个出现点和原句。
- [图表题注与标签清单](build-latex-manuscript/float-catalog)。按每个图表环境收集其题注、标签和所在源文件，方便合稿定编号。
