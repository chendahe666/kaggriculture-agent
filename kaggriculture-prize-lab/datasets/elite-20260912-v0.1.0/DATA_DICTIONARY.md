# 数据字典 / Data dictionary

单位：游戏内金币 coins、物品件数 units、离散回合/日。所有明确后缀 `_utc` 的时间为 ISO-8601 UTC；Kaggle 原始无时区字符串保留为 `_raw`，不伪造接口未提供的时区标记。

## 标识与时间

|字段|类型|含义与限制|
|---|---|---|
|episode_id|integer|官方对局 ID，去重与连接主键|
|seat|integer 0/1|该对局席位，不代表先后行动优势|
|team_id, team_name|integer, string|官方队伍 ID 和公开显示名|
|submission_id / selected_submission_id|integer|本次采样绑定的版本 ID，不是源码哈希|
|rank_at_batch_snapshot|integer|冻结批次时的名次，1 为榜首；非赛前名次|
|leaderboard_score_at_batch_snapshot|number|同一榜单响应中的动态评分，不是终局金币|
|selected_submission_score_during_metadata_collection|number|随后元数据请求中返回的提交评分，可能已与榜单快照有微小漂移|
|batch_snapshot_started_utc|datetime|本机开始冻结批次的时间；不是逐队评分的精确观测时刻|
|cohort_frozen_utc|datetime|提交和对局 ID 清单冻结完成时间|
|submission_date_raw|datetime string|官方返回的提交时间原文|
|episode_end_time_raw|datetime string|官方返回的对局结束时间原文|
|episode_source_timezone_assumption|string|本项目将无偏移服务端时间解释为 UTC；保留原文便于审计|
|download_started_utc, download_completed_utc|datetime or null|有明确客户端记录时才填写；未知不得回填估计|
|file_written_utc|datetime|原始文件修改时间，可近似反映写入完成；文件被复制/修改会影响它|
|acquisition_time_basis|string|client_clock 或 filesystem_mtime_proxy_only；说明时间证据强度|
|registered_utc|datetime or null|登记/重新核验记录的时间，非首次下载时间|
|cache_hit_at_registration|boolean or null|本次登记是否复用了本机文件；早期未记录则 null|
|rank_before_episode, rating_before_episode|null|本轮没有可信赛前排名/评分，明确缺失|

## 来源与质量

|字段|含义|
|---|---|
|replay_sha256, replay_bytes|源 JSON 原始字节 SHA256 和大小；用于重新获取后的核对|
|source, reacquire_command|数据来自官方公开回放接口；命令使用者须自行具备合法权限|
|source_submission_ids|该局在本次清单中关联的入选提交，可能含两队|
|selected_reference_count|该局贡献几条入选选手记录；独立对局数仍为 1|
|split|本版全部为 development，不伪装成 holdout|
|audit_status|not_run/pass/fail，表示逐状态与经济守恒校验状态|
|state_mismatches|模拟重放与录像的观测状态差异数，合格为 0|
|rewards_match|模拟终局奖励是否等于录像奖励|
|cash_balance_error|初始金币 + 实际销售 - 实际采购 - 雇佣 - 买地 - 终局金币，合格为 0|
|wheat_balance_error|初始麦库存 + 实际收获 + 买入 - 喂养 - 卖出 - 丢失 - 最终库存，合格为 0|
|audit_version|实际执行的统计口径版本|
|raw_replay_redistributed|始终 false；本数据包不含原始回放|

## 结果与经济流水

`final_coins`、`opponent_final_coins`：双方最终游戏金币。`final_coin_margin` 为本方减对手；`outcome_points` 为胜 1、平 0.5、负 0。`shops_in_unlock_order` 是事后完整商店序列，**不是开局可用特征**。

`harvest_units`：实际进入单位携带库存的收获，不是田间全部生产潜力；`feed_units`：成功 FEED 消耗；`purchased_units`：成功逐单位 BUY，键如 BUY_PRODUCT:WHEAT；`sold_units`：实际销售。`purchase_cost_by_order_item`、`sale_revenue_by_item` 为实际金币流，前者不包括另计的雇佣和土地。`overflow_units_by_item` 为 DROP 或每日归仓超过仓容导致的丢失，不包含田间腐烂、未收获或动物逃走。

`metrics` 汇总字段：

- money=final_coins；wheat_harvest/feed/bought/sold 为上述对应件数。
- wheat_buy_cost 为买入小麦总花费；wheat_net_trade_cash=卖麦收入−买麦花费；wheat_seed_cost 为麦种花费。**麦现金净额不是作物净利润。**
- hire_cost、land_cost、sale_revenue、purchase_cost 为对应实际金币总量。
- overflow_units、wheat_overflow 为全物品/小麦归仓丢失量。
- milk_harvest、wool_harvest、strawberry_harvest 为实际收获件数。
- fertilizer_bought 为外购肥料件数；fertilizer_used 为成功施肥消耗，不等于带来额外产量的有效施肥次数。
- labor_requests 为引擎处理的单位动作请求数，含 PASS/无效/移动，不是有效劳动产量。
- same_day_buy_sell_days 为同日既买又卖麦的天数，是周转线索，不等于已证明的无效交易。

## 日表

day_index 从 0 开始；harvest 为当日实际收获字典，feed 为当日饲喂消耗的小麦数；wheat_bought/sold/cost/revenue 为当日实际麦交易；hire_cost 为当日雇佣花费；labor_requests 含无效请求。最后一天只有实际执行的回合，不补造不存在的 step 719 动作。

## 完整性与运行记录

quality.json：入选/独立对局/有效选手行/日行数量、缺失与无效对局 ID、重复主键、准确下载时间与近似时间数量、保留本机的原始字节总量。

analysis-run.json：导出时间、Python/引擎版本、源清单和分析代码哈希、分析单位和数据用途。checksums.json 覆盖除自身外的发布文件，修改任何发布文件后必须重新生成。
