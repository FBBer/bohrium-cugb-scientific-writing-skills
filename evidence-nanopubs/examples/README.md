# Nanopublication

要把论文发现拆成可引用、可追溯的单条断言。每条断言连回原句，能区分直接观察、推断和否定。

## 试用示例

把一条自写传感器结论拆为带遮挡条件、极性与出处的断言，导出四个 TriG 命名图。伪造引句的副本应进入未决清单。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把论文材料交给加载该工具的 Agent，指定要发表的声明范围。已整理的声明可直接导出。

```sh
python3 scripts/nanopubs.py work/sources.json work/claims.json output
```

output/nanopubs.trig 与 assertions.json。断言、出处与发布信息可分别读取。

[完整用法和输入格式](../SKILL.md)
