# 公开高分方案研究

检索日期：2026-09-02。

Kaggle 页面分数会随 Notebook 版本和榜单环境变化。本文把“历史最好成绩”和“当前可下载产物”分开记录，不将它们混为同一版本。

## 方案与证据

| 方案 | 公开成绩/状态 | 可借鉴点 | 本地状态 |
| --- | --- | --- | --- |
| Rayk, *Kaggriculture: Rank Your Agent* | Notebook 历史最好 2990.4（V11）；当前 V23 页面 2563.4 | 根据商店顺序选择畜牧路线、抢售高价产品、限制终局种子、路线锁定 | 当前 V23 已保存为 K320 基线 |
| COK-ZhangZiliang/Kaggriculture | 仓库文档记录 V5 公开分 2735.4；V10 是后续公开版本 | 五类路线、执行保护、可复现测试和联赛框架 | V10 仓库已完整保存并通过测试 |
| Igor, *Multi-Route Farming Agent* | 历史最好 2767.3（V59）；当前 Notebook 版本/分数不同 | 由早期商店顺序选择 yarn-led、milk-supported、balanced 等固定路线 | 记录为下一批对手候选，未复制到当前候选 |
| Andrey Sokolovsky, *Kaggriculture* | 历史最好 2671.3（V10） | 可作为第三方风格对手，减少只对单一基线过拟合 | 待加入联赛 |
| lonespear/kaggriculture | 公开策略复盘，无统一可比的当前分数 | 畜牧 + CARE 经济、市场需求优先、售卖节奏、行动利用率、终局草莓 | 已提炼为优化方向 |

## 共识策略

1. 市场需求和商店出现顺序通常比静态基础价格更重要。
2. 奶牛/绵羊与 CARE 形成稳定经济引擎，但购买数量和路线应适应早期公开状态。
3. 高价商品应分批售卖，避免一次性击穿需求；终局则要优先兑现库存并减少无回报投入。
4. 农场布局、手牌路径和“有效行动占比”会显著影响最终产量。
5. 只打赢 starter 不足以证明强度；需要多种风格对手、双座位、训练/留出种子和最差表现门禁。

## 合规边界

- 只使用游戏公开观测状态做决策。
- 不根据种子值、对手文件名、对手身份或未公开内部状态选择动作。
- 所有改动保留来源、许可证和可复现实验记录。
- 当前 Rayk 文件是公开轨迹的行为重建产物，不应描述成作者未公开的隐藏源码。

## 公开来源

- 官方智能体指南：https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/AGENTS.md
- 官方排行榜：https://www.kaggle.com/competitions/kaggriculture/leaderboard
- Rayk Notebook：https://www.kaggle.com/code/raykkretzschmar/kaggriculture-rank-your-agent
- COK 公开仓库：https://github.com/COK-ZhangZiliang/Kaggriculture
- Igor Notebook：https://www.kaggle.com/code/flexonafft/kaggriculture-multi-route-farming-agent?scriptVersionId=342313226
- Andrey Notebook：https://www.kaggle.com/code/andrewsokolovsky/kaggriculture
- lonespear 策略仓库：https://github.com/lonespear/kaggriculture
