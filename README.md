# 科研阅读与学术写作工具

这里有十个可单独使用的工具，来自 Bohrium 中国地质大学（北京）站第一期。先按手头的材料选一项，打开“用法和示例”即可试跑。[比赛主页](https://play.bohrium.com/station/cugb/p1)

| 手里的材料或问题 | 能拿到什么 | 用法和示例 |
| --- | --- | --- |
| 双栏 PDF、合并表头或带扫描页的论文。 | 按阅读顺序取得正文，保留表格、列单位和页码。 | [文献文档解析](pdf-reading-order/examples/README.md) |
| 要保留数值、否定、公式和引文的外文论文。 | 逐段得到原文与译文，发现数量、段序和术语的变化。 | [文献翻译](align-paper-translation/examples/README.md) |
| 需要复用的论文摘录、实验观察与研究限制。 | 得到能回到原句的阅读笔记，并按主题或论文比较。 | [文献总结与结构化笔记](evidence-notebook/examples/README.md) |
| 要把论文发现拆成可引用、可追溯的单条断言。 | 每条断言连回原句，能区分直接观察、推断和否定。 | [Nanopublication](evidence-nanopubs/examples/README.md) |
| 论文中的同名实体、关系以及想查询的问题。 | 查出有原文支持的关系、方向和条件，打开对应子图。 | [文献知识图谱构建](paper-evidence-graph/examples/README.md) |
| 有语法问题、又需要保住数据与研究结论的原稿。 | 得到可直接使用的修订稿，并能逐句追查具体改动。 | [学术语言润色](audit-academic-edits/examples/README.md) |
| 重排过的论文正文，加上原始参考文献库。 | 按首次引用顺序重排编号、合并重复记录，保留公式里的下标。 | [参考文献与引用管理](reconcile-citations/examples/README.md) |
| 自己的研究问题与用于比较的论文。 | 获得有文献依据的引言，并看清研究空白适用于哪些条件。 | [引言与相关工作写作](ground-introduction/examples/README.md) |
| 实验记录、配置文件和实际运行日志。 | 还原用的参数、数据划分和实验条件，标明冲突与未记录的单位。 | [方法与实验章节写作](reconstruct-methods/examples/README.md) |
| 含主文件、子文件、参考文献和图片的 LaTeX 工程。 | 得到可交给他人重编的源码与 PDF，缺文件时能找到出错位置。 | [LaTeX 写作与编译](build-latex-manuscript/examples/README.md) |

进入选定的作品目录，运行 `python3 examples/demo.py ./my-example`，然后打开 `my-example/output/reading.html`。每份示例还会输出该题的可编辑文件与原始记录。需要直接用自己的论文时，按相应工具说明传入材料。

Python 3.9 及以上可运行文本处理工具。PDF 解析使用 PyMuPDF 或 Poppler，扫描区域识别另需 Tesseract 和相应语种数据。LaTeX 需要与原模板匹配的引擎及宏包，BibTeX 输入可用 Pandoc 读取。翻译和润色可输出 Word 双语稿或原生修订，用 python-docx 生成，以 LibreOffice 渲染 PDF。
