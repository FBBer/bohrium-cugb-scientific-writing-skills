# 文献知识图谱构建

论文中的同名实体、关系以及想查询的问题。查出有原文支持的关系、方向和条件，打开对应子图。

## 试用示例

从单条自写观测抽取一个方法和一个任务，分别查询支持方向、反向关系与类型，验证回查到原句。命中的第一和第三条查询分别输出 query-01-01 与 query-03-01 的可编辑 SVG、PDF 与 PNG。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把论文和自己的查询交给加载该工具的 Agent。按示例整理实体、关系和查询后运行。

```sh
python3 scripts/graph.py work/sources.json work/graph-plan.json output
```

output/graph.graphml、queries.json 和 figures/。查询结果附原句与位置。

[完整用法和输入格式](../SKILL.md)
