# P3 V5-low-file — 研究候选，不晋级

建档日期2026-09-12。假设：放宽72步入口后，内置low完整生产路线可能更强，并与原版互补。只改变连续合法历史上的路由；保留执行、市场、修复和账本；不混入P2。

文件：`experiments/track-portfolio-20260912/v5-low-file/main.py`，204845字节。
SHA256：`f2d250860f199ba5569cfbd9909219a0069da6a1c3575fe4203c5d1551e5a3a2`。
父基线SHA：`1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`。

方法：72进入V5，168固定low；missed168仍safe-low，不退回旧布局。实际官方last-callable入口为`_p3_portfolio_entrypoint`。

评价：6对手、4开发seed、双座位，48次新720帧对局对48个只读P2控制。全部双DONE、无错误、正确触发、无回退。原版35W2T11L、36胜分；本版32W0T16L、32胜分。五族等权.85→.80；3胜转负、2平转负、0升级。平均金币分差虽+3426.708，不能替代官方胜负目标；Arlene仍0/8。最大本机外层调用108.519ms，不是官方沙箱认证。

结论：REJECT，无本批胜负互补，不训练选择器，不提交、不替换原版。完整方案、经济边界与结果见`reports/p3-20260912-report.md`和`results/portfolio-20260912/probe-report-v1.json`。中间候选提交用于按版本恢复；完整复现工具见轮次收尾checkpoint。沿用COK许可及来源声明。
