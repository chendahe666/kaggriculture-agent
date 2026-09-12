# cycle-horizon4-rerank

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/cycle-20260911/horizon4-rerank/main.py`
- SHA256：`7af86db3e6d91e6b9d869d8be2db1ee7a2c6df20e5cb6668ffd54cb452e904bc`
- 基线：K320（完整基线哈希见 opponent-pool.json）
- 假设：窗口和排序可能有互补收益。
- 方法：组合窗口 4 与最终排序。
- 评估：7 场 fixed-tape；闭环 91101–91104，双座位、COK/Seyam/原版各 8 局。
- 实际结果：回放 4/0/3；闭环对 COK 0/8 胜，对另两者各 8/8 胜。
- 结果文件：`results/cycle-h4rank-replay.json`、`results/cycle-h4rank-live-dev.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**hold**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
