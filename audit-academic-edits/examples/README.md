# 学术语言润色

有语法问题、又需要保住数据与研究结论的原稿。得到可直接使用的修订稿，并能逐句追查具体改动。

## 试用示例

修正两句自写物理测量原稿的主谓一致和分词，保留否定关系、5 mm 与图号。演示对照故意改变单位的稿件。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把原稿和投稿语言要求交给加载该工具的 Agent。已有改稿时可比对示例结构的两份文件。

```sh
python3 scripts/prose.py edit work/segments.json work/edits.json output --strict
```

output/revised.md 和 audit.json。数值或否定范围出现疑点时，会把候选稿单独保存。

[完整用法和输入格式](../SKILL.md)

需要实际的 Word 文件及 PDF 预览时，在本工具的 prose.py 命令后加 `--word --preview`。Word 使用 python-docx，PDF 使用 LibreOffice。

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

用本例的两段原稿试分批校改。运行 `python3 scripts/chunks.py split my-example/work/segments.json my-packets --chars 30`。对照 before 与 after，填入各段改文和理由，再用 `python3 scripts/chunks.py merge my-example/work/segments.json my-packets edits.json` 合稿。
