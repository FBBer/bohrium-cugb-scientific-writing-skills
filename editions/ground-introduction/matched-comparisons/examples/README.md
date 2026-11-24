# 引言与相关工作写作

自己的研究问题与用于比较的论文。获得有文献依据的引言，并看清研究空白适用于哪些条件。

## 试用示例

对两篇自写研究说明和一份本研究设计做同维度比较，从静态测量的范围推导有边界的空白，然后把研究目的回连到本研究方案。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把研究目的、已知结果与对照文献交给加载该工具的 Agent。按示例准备论断与证据后运行。

```sh
python3 scripts/compose.py introduction work/sources.json work/intro-plan.json output --strict
```

output/introduction.md 与 comparison-matrix.json。需要追溯时可打开逐句来源表。

[完整用法和输入格式](../SKILL.md)

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

将本例的引言和具体论断所引的原句一起交给合作者。

```sh
python3 scripts/compose.py introduction my-example/work/sources.json my-example/work/intro-plan.json my-example/output --word --preview
```

## 从普通文稿整理引文和贡献

先根据原文写四段，分别交代背景、同一问题下的既有做法、这些研究留下的具体缺口及本文贡献。每行写一个或几个有关联的论断，在相应从句末放 Markdown 脚注 `[^key]`。文末的脚注定义给出 `材料相对路径 | 原句`。同一句在文献中出现多次时，在路径后加 `#位置`，位置取自原文索引。用 `--own` 指明本文的记录，其余材料作为参考文献。下面的短文为自拟示例。

```sh
python3 scripts/manuscript.py examples/synthesis/papers examples/synthesis/draft.md intro-output --own our-log.txt --bibliography examples/synthesis/references.json --language en --strict
```

`introduction.md` 可直接放进稿件，参考文献按首次出现顺序排列。`claim-sources.tsv` 保留每个从句的出处与原句，`related-work.tsv` 汇总已有工作和空白，`contributions.tsv` 单列本文证据。找不到引文、归错研究或扩大限定范围的行留在 `manuscript-sources.json` 供作者修改。同一测量值若涉及不同文献，分别在各自的从句后引证。自动核对涵盖直接数量、来源和范围；没有独立元数据时保留文件名。作者最终核对转述含义。材料、文稿和输出分别存放。
