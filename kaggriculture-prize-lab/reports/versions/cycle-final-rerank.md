# cycle-final-rerank

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/cycle-20260911/final-rerank/main.py`
- SHA256：`f5da6e409cb455d1b11340698e47be15730d8698eba57a9c54677b5a0d6ede9b`
- 基线：K320（完整基线哈希见 opponent-pool.json）
- 假设：最终订单重新排序可改善成交。
- 方法：原 agent 返回后重新排列销售槽位。
- 评估：7 场旧回放 fixed-tape，全部开发集。
- 实际结果：3/0/4，原版 2/1/4；没有本版本新增闭环晋级证据。
- 结果文件：`results/cycle-rerank-replay.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**hold**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
