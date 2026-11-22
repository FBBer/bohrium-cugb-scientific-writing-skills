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

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

导出这个样例的 Word 和 PDF，点笔记中的序号可阅读证据。

```sh
python3 scripts/compose.py notes my-example/work/sources.json my-example/work/notes-plan.json my-example/output --word --preview
```

## 从一组论文直接做笔记

把论文放进一个目录，运行下面的命令。可读取有文字层的 PDF、Word、Markdown 和纯文本。示例包含两篇自拟的中英文短文。

```sh
python3 scripts/notebook.py examples/papers reading-notes --focus 漂移 --focus drift
```

先读 `reading-notes/notes.md`，再按编号找到原文。`study-matrix.tsv` 把各篇论文的同类证据并排列在一张表中。`comparison.tsv` 按论文、研究问题、方法、发现、作者解释和局限列出原句；`reading-cards.json` 另存位置和字符范围。只有正文中出现的内容才进入笔记。缺少哪一类原文记在 `uncovered`，原文中的参考文献列表不参与摘录。多材料目录可重复添加 `--paper 相对路径`。`--language en` 使用英文栏目；`--per-role 4` 可增加各栏摘录。输出放在材料目录之外。手写解释或跨论文综合时，用下方的 compose 工作流。
