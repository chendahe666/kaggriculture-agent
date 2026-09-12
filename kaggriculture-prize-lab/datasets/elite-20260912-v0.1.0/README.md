# Kaggriculture Elite Strategy Observatory — v0.1.0

可复现的强手策略观察数据集 / Reproducible derived economics from public Kaggriculture episodes.

## Status / 状态

本目录为发布候选，最终是否完整以 quality.json 的 complete 为准。许可证方案等待项目所有者确认；原始回放的再分发权限没有确认，因此**不包含原始录像、完整动作带、私有库存序列或选手源码**。不能将本目录的许可扩展到 Kaggle 平台内容。

## Purpose / 用途

分析强手在不同商店、生产布局和市场环境下的经济行为，支持提出可证伪的优化假设。不是 Kaggle 官方数据集，不代表主办方认可；不声称识别选手的私有算法，不提供保证提分的策略。

## Collection / 采集口径

2026-09-11（America/Chicago），对应 UTC 2026-09-12。冻结一次前 30 名榜单快照，每队选官方客户端返回的当前最高分活跃提交，取其最新 20 场已完成 PUBLIC 比赛，不按胜负筛选。600 条选手记录去重为 438 场比赛。排名随时间变化；本数据集保留采集批次快照，不随榜单更新而改写历史。

`rank_at_batch_snapshot` 和 `leaderboard_score_at_batch_snapshot` 是采集批次快照，**不是对局发生前的排名/实力**。`final_coins` 才是单场游戏金币。不能把金币与排行榜 rating 混为一谈，也不能用采集后榜单评分充当历史预测特征。

早期下载没有客户端开始/完成时间记录：这些字段保持 null，另提供 `file_written_utc`，只作为近似下载完成时间。重新核验缓存的时间在 `registered_utc`，绝不冒充首次下载时间。查看 DATA_DICTIONARY.md。

## Files / 文件

|文件|粒度|用途|
|---|---|---|
|cohort.jsonl|每个选手一行|排名/评分快照、固定提交、采集批次|
|COLLECTION_RECORD.md|本批摘要及 30 队表格|直接阅读采样时间、名次、分数和固定版本|
|episodes.jsonl|每个独立对局一行|来源、时间、SHA256、下载时间精度、复现质量|
|players.jsonl|每个入选选手的对局席位一行|实际产销与成本、终局金币、胜负、经济守恒|
|daily_economics.jsonl|每个入选席位每日一行|按日汇总实际收获、饲喂、买卖与劳动请求|
|analysis-run.json|每次数据导出一份|版本、方法、环境和分析源代码哈希|
|quality.json|每次导出一份|覆盖、缺失、失败、重复键及时间精度计数|
|checksums.json|每个发布文件一项|发布文件完整性校验|

JSONL 为 UTF-8，每行独立 JSON；空缺为 null，不填 0。主要连接键是 episode_id；席位级键是 (episode_id, seat)，日级再加 day_index。共用同一比赛的两个入选选手不是独立比赛样本。

## Reproduce / 复现

在仓库根目录，Python 3.13，安装 kaggle-environments==1.32.7；获取原始数据需要使用者自己的 Kaggle 登录及适用权限，不共享凭据。

1. 使用 episodes.jsonl 的 reacquire_command 下载公开回放，核对 replay_sha256。若远端数据失效或权限变化，不保证未来仍可重新获取。
2. 原始回放放到 kaggriculture-prize-lab/inbox/replays；本轮冻结清单在 results/elite-20260912/，**不要重新运行 plan 改写队列**。
3. 运行 `py -3.13 kaggriculture-prize-lab/scripts/elite_economics.py`。
4. 运行 `py -3.13 kaggriculture-prize-lab/scripts/summarize_elite.py`。
5. 运行 `py -3.13 kaggriculture-prize-lab/scripts/build_elite_dataset.py --require-complete`。
6. 运行 `py -3.13 kaggriculture-prize-lab/scripts/validate_elite_dataset.py` 校验主外键、日表汇总、时间口径和文件哈希。
7. 运行 `py -3.13 -m unittest discover -s kaggriculture-prize-lab/tests -q`。采集时间、文件写入时间和导出时间不会在其他机器逐字重现；经济结果应在相同源数据、引擎和分析代码下复现。若审计目录已有结果，分析器会跳过；独立重算应在新的工作副本使用空审计目录，保留发布原件，完成后比较经济字段。

## Quality and limitations / 质量与局限

- 引擎逐帧状态与终局奖励一致后，才接受该局经济标签；另核验金币收支与小麦物量守恒。通过不能证明所有未测试指标均正确。
- 统计成功执行的操作，而不是把 BUY/SELL 请求数量直接当成交量。
- 所有本批记录均为开发资料，没有对外宣称的独立测试集。训练/评估应按时间、提交版本、对局和策略类型隔离，不能随机拆帧。
- 榜单前 30 名有幸存者偏差，近期匹配并非随机；不能外推到全体选手或把观察相关性当因果效应。
- 同一选手在不同商店下可能使用不同路线。行为分组不等于独立源码家族。
- 买卖麦现金净额未扣种子、劳动和地块机会成本，不是种麦利润。同日买卖也不自动说明浪费。
- 本数据主要是事后分析标签。最终商店列表、终局结果和未来日统计不可直接作为在线决策输入；任何策略特征必须来自当时合法观测。

## Attribution / 来源与引用

Source: [Kaggriculture competition](https://www.kaggle.com/competitions/kaggriculture), [official environment and agent guide](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture). Public team display names are preserved for provenance, not to assert private identity or source authorship.

建议引用本仓库、数据集版本、Git 提交哈希与采集批次时间。原始游戏与平台内容权利属于各自权利人；本项目贡献是采集索引、可复现审计代码、衍生统计及研究记录。
