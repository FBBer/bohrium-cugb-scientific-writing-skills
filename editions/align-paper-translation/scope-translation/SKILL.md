---
name: align-paper-translation
description: 将科研文献按段翻译并核对否定范围、必要条件、可能性和显著性措辞。
metadata:
  author: GPT-6.2Astra
---

# 译文里的条件与否定

先完整翻译指定章节，保留标题、图表、公式、引文、数字和单位。按语境确定术语和指代。将每个有逻辑限定的独立分句写入 segments，每项给出 id、evidence（source、loc、quote）与实际 translation。仅当、只有、除非、尚无证据等要回到原文决定。脚本识别的有限词型用于提示回读，合法灵活译法由读者和上下文判断。译文有问题时改写后重跑，不把建议当作成稿。

## 使用本题材料

读取 /input/case.json、task.md 和列出的附件。把示例命令中的输入换成本题实际文件。将主结果按场景指定的字段和文件名写入 /app/output，保留原 case_id、来源和不确定项。完整的通用处理入口见 [FULL_WORKFLOW.md](FULL_WORKFLOW.md)。

```sh
python3 scripts/logic_translation.py sample/sources sample/plan.json /tmp/qualified-translation
```

网页与纯文本交付全篇；translation.json 保存逐段定位，review 列出需要重读的句子。示例把‘并非所有’和‘均不’分清，把不可区分的实验结果保留为统计表述。

[打开示例成品](sample/preview/translation.html)。sample/ 使用自拟材料。文本处理需要 Python 3.9 或以上；Word、PDF、Excel 的可选依赖和通用工作流见随附说明。

作品署名　GPT-6.2Astra
