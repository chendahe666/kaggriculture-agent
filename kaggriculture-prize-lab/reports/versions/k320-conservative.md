# k320-conservative

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/k320-conservative.py`
- SHA256：`547406e768a404682f0d0bbadece6a94380fc44fb5c635bafbc22e9d0dc9abe3`
- 基线：K320（完整基线哈希见 opponent-pool.json）
- 假设：联合禁用两机制能否规避错误交互。
- 方法：同时禁用抢售与路线反制。
- 评估：COK，20260811/20260829，双座位 4 局。
- 实际结果：0/0/4，平均金币差 -2203.75。
- 结果文件：`results/conservative-screen.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**reject**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
