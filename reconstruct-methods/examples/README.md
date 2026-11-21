# 方法与实验章节写作

实验记录、配置文件和实际运行日志。还原用的参数、数据划分和实验条件，标明冲突与未记录的单位。

## 试用示例

比较同一采集过程的默认 20 ms 和运行日志的实际 15 ms，记录两处来源和采用实际配置的理由。未给出的随机种子需保留为缺口。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把配置和日志交给加载该工具的 Agent，说明要复现哪一次运行。按示例准备方法计划后运行。

```sh
python3 scripts/compose.py methods work/sources.json work/methods-plan.json output --strict
```

output/methods.md、parameters.json 和 reproduction.json。数值、单位和所属运行分别保留。

[完整用法和输入格式](../SKILL.md)

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

## 铝梁重装试验

附带一组为教学构造的夹具记录。旧草案给两个夹具写了同一加载质量，实际记录按简支、固支分别给出砝码、支距和重复数。下面的 Word 含可编辑参数表，正文及表值可跳到原始实验格。

```sh
python3 scripts/casework.py index --input examples/beam/input --work beam-work
python3 scripts/compose.py methods beam-work/sources.json examples/beam/plan.json beam-output --word --preview
```
