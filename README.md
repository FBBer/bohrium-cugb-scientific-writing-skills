# 科研阅读与学术写作工具

本仓库收录 Bohrium AI 产品周赛中国地质大学（北京）站第一期的十个独立作品。每个目录均可单独安装，包含 Agent 使用说明、可执行脚本和自写的最小示例。[比赛主页](https://play.bohrium.com/station/cugb/p1)

| 作品 | 复现入口 |
| --- | --- |
| [文献文档解析](pdf-reading-order/SKILL.md) | [运行示例](pdf-reading-order/examples/README.md) |
| [文献翻译](align-paper-translation/SKILL.md) | [运行示例](align-paper-translation/examples/README.md) |
| [结构化阅读笔记](evidence-notebook/SKILL.md) | [运行示例](evidence-notebook/examples/README.md) |
| [Nanopublication](evidence-nanopubs/SKILL.md) | [运行示例](evidence-nanopubs/examples/README.md) |
| [文献知识图谱](paper-evidence-graph/SKILL.md) | [运行示例](paper-evidence-graph/examples/README.md) |
| [学术语言润色](audit-academic-edits/SKILL.md) | [运行示例](audit-academic-edits/examples/README.md) |
| [参考文献与引用管理](reconcile-citations/SKILL.md) | [运行示例](reconcile-citations/examples/README.md) |
| [引言与相关工作写作](ground-introduction/SKILL.md) | [运行示例](ground-introduction/examples/README.md) |
| [方法与实验章节写作](reconstruct-methods/SKILL.md) | [运行示例](reconstruct-methods/examples/README.md) |
| [LaTeX 写作与编译](build-latex-manuscript/SKILL.md) | [运行示例](build-latex-manuscript/examples/README.md) |

## 运行方式

进入相应目录，按示例说明运行 Python 3.9 或更高版本。各工具将合成输入、工作记录、可编辑产物和校验结果写到用户指定的示例目录。使用新材料时，让 Agent 按该目录的 SKILL.md 处理实际文件。主结果遵循调用者给出的字段与格式。

文本处理可使用 Python 标准库。PDF 解析使用 PyMuPDF 或 Poppler，扫描区域识别另需 Tesseract 及相应语种数据。LaTeX 需要 TeX 引擎及原模板依赖。BibTeX 导入可使用 Pandoc。各作品的说明列出工具缺失时的处理方式。数据定位、证据校验和差异报告可独立复用；数值相符或引文逐字匹配后，仍应回到原文核对主体、推论和适用条件。
