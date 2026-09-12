# cycle-horizon6

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/cycle-20260911/horizon6/main.py`
- SHA256：`76d3680b466be3ee0c6b033255609798932668b485ef985264e25a3117759bc5`
- 基线：K320（完整基线哈希见 opponent-pool.json）
- 假设：更长抢售窗口可能改善市场兑现。
- 方法：抢售计划窗口设为 6，保留原底座。
- 评估：7 场 fixed-tape；闭环 91101–91104，双座位、COK/Seyam/原版各 8 局。
- 实际结果：回放 5/0/2；闭环对 COK 1/8 胜，对另两者各 8/8 胜。
- 结果文件：`results/cycle-horizon6-replay.json`、`results/cycle-h6-live-dev.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**hold**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
