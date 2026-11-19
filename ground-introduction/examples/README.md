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
