# market-sweep-rank

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/track-market-20260911/sweep-rank/main.py`
- SHA256：`91f6586f0ee0f75f36fbeacc3e8e46423f2eb5ddf2f7ea5d42c15f871e564be0`
- 基线：COK V10（完整基线哈希见 opponent-pool.json）
- 假设：补售与排序组合可改善槽位利用。
- 方法：组合需求限量补售与排序。
- 评估：COK/Igor/lonespear × 91101/91102 × 双座位，共 12 局。
- 实际结果：12/0/0；没有证明真实线上提升。
- 结果文件：`results/track-sweep-rank-screen.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**hold**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
