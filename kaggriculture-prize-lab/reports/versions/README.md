# 逐版本索引

这些提交补录已有实验，提交时间是建档时间。每个候选提交同时包含独立代码和报告，提交正文也记录假设、方法、实际评估与结论。

当前线上基线：[COK V10](cok-v10-baseline.md)，默认入口迁移提交 [92676d9](https://github.com/chendahe666/kaggriculture-agent/commit/92676d9)。根代码不采用以下实验版。

| 版本 | 建档提交 | 结论 |
|---|---|---|
| [k320-no-preempt](k320-no-preempt.md) | [dd2c8f7](https://github.com/chendahe666/kaggriculture-agent/commit/dd2c8f7) | reject |
| [k320-no-family-counters](k320-no-family-counters.md) | [3c74377](https://github.com/chendahe666/kaggriculture-agent/commit/3c74377) | reject |
| [k320-conservative](k320-conservative.md) | [9b21f46](https://github.com/chendahe666/kaggriculture-agent/commit/9b21f46) | reject |
| [cycle-final-rerank](cycle-final-rerank.md) | [6fe7ff8](https://github.com/chendahe666/kaggriculture-agent/commit/6fe7ff8) | hold |
| [cycle-horizon4](cycle-horizon4.md) | [de19ee0](https://github.com/chendahe666/kaggriculture-agent/commit/de19ee0) | hold |
| [cycle-horizon6](cycle-horizon6.md) | [a2ab55e](https://github.com/chendahe666/kaggriculture-agent/commit/a2ab55e) | hold |
| [cycle-horizon4-rerank](cycle-horizon4-rerank.md) | [09d17c8](https://github.com/chendahe666/kaggriculture-agent/commit/09d17c8) | hold |
| [cycle-horizon4-floor-guard](cycle-horizon4-floor-guard.md) | [db85c93](https://github.com/chendahe666/kaggriculture-agent/commit/db85c93) | hold（未测试） |
| [market-rank](market-rank.md) | [a6967b2](https://github.com/chendahe666/kaggriculture-agent/commit/a6967b2) | hold |
| [market-sweep](market-sweep.md) | [5cddcfb](https://github.com/chendahe666/kaggriculture-agent/commit/5cddcfb) | hold |
| [market-sweep-rank](market-sweep-rank.md) | [8125ec6](https://github.com/chendahe666/kaggriculture-agent/commit/8125ec6) | hold |
| [market-integrated](market-integrated.md) | [10f64d8](https://github.com/chendahe666/kaggriculture-agent/commit/10f64d8) | reject |
| [market-gated](market-gated.md) | [8df4963](https://github.com/chendahe666/kaggriculture-agent/commit/8df4963) | hold |

完整轮次的可恢复快照见 Git 标签 `research-checkpoint-20260911`。早期 V4.2 对照为 `c7bbcd6`。不把 hold 解释为发布通过，不根据本地金币差预测 Kaggle rating。
