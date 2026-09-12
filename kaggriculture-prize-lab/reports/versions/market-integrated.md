# market-integrated

建档：2026-09-11；对既有实验补建 Git 档案，不伪造实验时间。

- 代码：`experiments/track-market-20260911/integrated/main.py`
- SHA256：`d700dee5bb611704a98dc5b81371ca192ab49f7e806f1a5052e7fd6ee54692cc`
- 基线：COK V10（完整基线哈希见 opponent-pool.json）
- 假设：库存投影和观察记账能让补售、排序联动一致。
- 方法：整合排序、补售、工作后库存投影和最终动作记账。
- 评估：三对手 × 91101–91104 × 双座位；另用近期连续 20 场 fixed-tape 反证。
- 实际结果：闭环 23/0/1；近期回放从基线 7 胜降至 6 胜，虽平均分差改善 145。107992327 从 +382 变 -2508。
- 结果文件：`results/track-integrated-dev.json`、`results/track-integrated-current-corpus.json`
- 评估口径：胜/平/负，不将金币差映射为 Kaggle rating。种子、对手哈希及逐局结果以对应 JSON 为准。
- 耦合与局限：市场、库存、饲料、行动缓存及商店 RNG 可能联动；fixed-tape 不会实时反应。旧同源/弱对手上的高胜率不证明对真实强手泛化。
- 下一步：保留复盘与消融价值；COK 为当前基线，按已批准的 Track P 做饲料/采购/生产/劳动联合诊断。不自动上传本候选。

唯一建议：**reject**。hold 仅代表研究保留，不是可提交版本。详细跨版本比较见 OPTIMIZATION_LOG.md；采购成本仅引用 canonical v2 审计。
