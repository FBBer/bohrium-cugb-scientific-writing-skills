---
name: evidence-nanopubs
description: 将有出处的科研结论拆为可单独验证的断言，生成带证据、来源与出版信息的四命名图 TriG。
---

# Nanopublication

每条断言只表达一个能独立判断的科研主张。写清主体、关系、客体、实验条件、方向与证据强度，附能定位的原句和来源版本。

先用 `python3 "$S/scripts/casework.py" index --input /input --work /app/work` 生成 sources.json。证据用实际 id 和原文 quote 对应。下面使用示例文件名。

```sh
S=/skills/weekly-skill
python3 "$S/scripts/nanopubs.py" /app/work/sources.json /app/work/claims.json /app/output
```

输出 assertions.json 和带四个具名图的 nanopubs.trig。若来源给出受控词表的实体或关系标识，可填 subject_iri、predicate_iri、object_iri；每个命题可以分别查询主体、关系和客体。

对主动句和被动句先辨明谁作用于谁。校准、使用、检测等常见关系会用引文核对方向，否定或推测保留其原有语气。

从 `/input/case.json` 读取 case_id 和本题 output_contract，把实际正文、证据和文件写到 `/app/output`，按原字段与类型填写 result.json。已有成稿可用 `casework.py check` 核对格式。题目指定可编辑文件和预览时，提交对应文件并打开预览核对。

[输入格式与领域处理](references/method.md) · [可运行示例](examples/README.md)
