# 文献知识图谱使用方法

命令中的 `S` 指当前工具目录。在平台上使用 `S=/skills/weekly-skill`，本地从工具根目录运行时使用 `S="$PWD"`。若题目需要中间计划，请按实际材料写入 `/app/work`。

计划含 nodes、edges 和 queries 三个数组。节点形如 {"key":"a","type":"method","label":"原名","scope":"学科/义项","document":"实际文件","aliases":[],"evidence":[{"id":"S","quote":"原文"}]}。关系含 source、target（局部 key）、predicate、scope、polarity（positive/negative/uncertain）、strength（direct/inference/quoted）、evidence。保留人名重名、全称/缩写的文内定义、不同任务下的同名模型。仅在有合并依据且类型兼容时给后出现的节点 same_as 和 merge_reason。以有证据的别名表保留原文拼写。

将共现、作者提出、经过验证、引用他人发现及推断区分开。直接关系的肯定或否定须与原句中同一对实体、同一谓词一致。若两篇论文在不同条件下得到相反结果，为每种条件分别保留关系和出处。“可能用于”一类引文按 uncertain 记录并保留原词。原文写“未观察到显著变化”时，在 scope 里写清统计条件或测量分辨率。直接关系的措辞如果包含转述、双重否定或省略的主语，先按原文辨认其含义，再决定它表示已观察到的事实、推断还是可能性。对相对关系写清 A 相对谁、指标越大还是越好。新增文献可用 --previous 读取既有 graph.json，以持久节点 ID 指明同一实体；核查已有边和证据未丢失。

从材料写至少三个真正不同的研究问题，覆盖方法和任务、指标或比较、以及未证实的关系。每项如 {"question":"哪个方法在此设置下与基线比较？","where":{"predicate":"compared_with","scope":"实际设定"},"source_type":"method"}。支持 source、target、predicate、scope、strength、polarity 过滤和 source_type/target_type。脚本返回实际命中子图与证据。多跳问题可按中间节点连接两次查询并列出各跳证据。

```sh
python3 "$S/scripts/graph.py" /app/work/sources.json /app/work/graph-plan.json /app/output
```

每个有依据的查询同时生成可编辑 SVG。实体旁的实色色标区分类型。标题、节点文字、关系和条件说明，以及连线和箭头均用纯黑色（#000000）。箭头从主体指向客体，关系名称在箭头上，适用条件在下。实线表示直接证据，虚线表示推断或转引，箭头下另标明具体类别。节点标签沿用原材料的写法。可用 PyMuPDF 时一并导出印刷版 PDF 和 PNG 预览。增量合并时，出处还保留案例标识与文本版本指纹；同一路径同一行的修订分开定位。原始关系保存在 graph.json，绘图代码位于 scripts/diagram.py。中文稿在图中沿用中文实体和关系标签，分组标题直接写该组回答的问题。

打开 graph.graphml、graph.json、queries.json，检查每条边有两端，每个回答的证据能回指正文。数字相同或名称相似不构成合并依据。空查询标记材料缺乏支持，追加实际问题的人类可读答案以及出现冲突时的并列解释。

常规纯文本案例仅需 Python 标准库。 JSON Schema 的完整校验可选装 jsonschema（本地实测 4.26.0）。正式评测优先采用镜像已有依赖；独立使用时在自己的环境配置。

多跳查询示例为 {"question":"样品经哪个方法得到哪项指标？","from":"specimen","to":"metric","steps":[{"predicate":"tested_by"},{"predicate":"measures"}]}。from、to 可以是计划的局部键或图中 ID，to 可省略。每步默认只取直接肯定关系，可明确指定其他 strength、polarity 或 scope。paths 中每一跳含独立证据，走到同一节点的两条路线分别保留。

对常见英文关系按完整句式区分主动、被动和显式限定。比如 B was calibrated by A 给出 A 对 B 的校准关系。资料只有别名或间接支持时，使用来源限定和相应的证据强度。
