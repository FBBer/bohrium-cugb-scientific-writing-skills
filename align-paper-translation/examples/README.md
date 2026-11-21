# 文献翻译

要保留数值、否定、公式和引文的外文论文。逐段得到原文与译文，发现数量、段序和术语的变化。

## 试用示例

将两段自写的光学实验描述译为中文，保留 10 ms、引文 [4]、图号和否定关系；对故意把计时数值改错的一份副本再次运行审计。

在作品目录运行，使用一个新的示例目录。

```sh
python3 examples/demo.py ./my-example
```

用浏览器打开 `my-example/output/reading.html` 阅读结果。输入样例在 `my-example/input/`，准备好的中间材料在 `my-example/work/`。

## 换成自己的材料

把论文、目标语种和术语偏好交给加载该工具的 Agent。已有段落与候选译稿时，可依照示例中的两个 JSON 文件运行。

```sh
python3 scripts/prose.py translate work/segments.json work/translation.json output --strict
```

output/bilingual.md。严格模式遇到需复核的译稿时保存在 candidate-bilingual.md，原因在 audit.json。

[完整用法和输入格式](../SKILL.md)

需要实际的 Word 文件及 PDF 预览时，在本工具的 prose.py 命令后加 `--word --preview`。Word 使用 python-docx，PDF 使用 LibreOffice。

自己的论文、Word 或实验表可直接放在同一目录，用 `python3 scripts/casework.py index --input materials --work work` 建索引；独立使用时无需另写比赛任务文件。

长稿可先在这个两段样例上分批。运行 `python3 scripts/chunks.py split my-example/work/segments.json my-packets --chars 40`，在各文件的 draft 中填写 target，`python3 scripts/chunks.py merge my-example/work/segments.json my-packets merged.json` 会依原次序合稿。
