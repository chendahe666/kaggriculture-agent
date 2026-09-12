# k320-no-preempt

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/k320-no-preempt.py`
- SHA256：`9ed766e530f70b8bb2b5395d6c2243082462491e1ac86363aa631181c61914ba`
- 基线：K320（完整基线哈希见 opponent-pool.json）
- 假设：禁用抢售，检验其是否造成负收益。
- 方法：关闭 premium 抢售逻辑。
- 评估：COK，20260811/20260829，双座位 4 局。
- 实际结果：0/0/4，平均金币差 -1474。
- 结果文件：`results/no-preempt-screen.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**reject**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
