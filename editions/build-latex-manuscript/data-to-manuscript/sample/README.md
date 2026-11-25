# 用同一份数据生成论文正文和表格 · 使用示例

这里的短文和数据均为自拟的使用示例。

示例将 1.245 ± 0.035 mm 按两位小数排成 1.25 ± 0.04 mm。零误差仍显示 0.00，未报告误差的另一行只显示读数。

在本作品目录用 Python 3.9 或以上版本运行。
示例使用 pdflatex、latexmk 和 booktabs。实际模板按其要求安装 TeX 引擎、字体与宏包。

```sh
python3 scripts/data_manuscript.py sample/sources sample/plan.json /tmp/data-to-manuscript-example
```

manuscript.pdf 和 source/ 是可以阅读与继续编辑的成品。measurement-sources.json 将正文键连回 CSV 行和原精度，build.json、compile.log 列出引擎与实际诊断。用交付的 source/ 再编译一次，查看有变动的正文与表格页。

本例需要改动输入时，可复制 sample/sources 与 plan.json。重新从 CSV 构建，表格、正文和来源记录会一起更新。
