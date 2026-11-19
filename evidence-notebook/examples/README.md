# 文献总结与结构化笔记

需要复用的论文摘录、实验观察与研究限制。得到能回到原句的阅读笔记，并按主题或论文比较。

## 试用示例

自写的观测报告包括方法、发现和限制。检验章节顺序、可检索关键词、每句引文以及读数的单位，额外篡改过的引文应被发现。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把论文和想回答的问题交给加载该工具的 Agent。材料索引与笔记计划的结构见示例中的 work 目录。

```sh
python3 scripts/compose.py notes work/sources.json work/notes-plan.json output --strict
```

output/notes.md、paper-cards.json 和主题索引。论文事实与读者解释分别标明。

[完整用法和输入格式](../SKILL.md)
