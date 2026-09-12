# P3 V5-high-file — 研究候选，不晋级

建档日期2026-09-12。假设：内置high完整生产路线可在部分公开状态优于原版或low。72进入后仍保持完整low包装链直到167，避免152步的未来买种剪裁提前分叉；168才固定high并保持。

文件：`experiments/track-portfolio-20260912/v5-high-file/main.py`，204846字节。
SHA256：`40c857218c781a5980010bacb348c03f498a87d36c2671e5a8c37194c78a2a83`。
父基线SHA：`1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`。

方法：不叠加P2，不复制Arlene；保留经济账本、执行与修复。漏过168回safe-low而不晚开high。实际官方last-callable入口为`_p3_portfolio_entrypoint`。

评价：6对手、4开发seed、双座位，48次新720帧对局对48个只读P2控制。全部双DONE、无错误、正确触发、无回退。原版35W2T11L、36胜分；本版32W0T16L、32胜分。五族等权.85→.80；3胜转负、2平转负、0升级。平均金币分差−3631.417；Arlene仍0/8，平均分差增量−10413。最大本机外层调用110.487ms，不是官方沙箱认证。

结论：REJECT。与low的48场胜负向量完全相同，三专家事后胜分上限仍等于原版。不训练选择器、不提交、不替换原版。完整方案与结果见`reports/p3-20260912-report.md`和`results/portfolio-20260912/probe-report-v1.json`。中间候选提交用于恢复源码；整套工具见收尾checkpoint。沿用COK许可及来源声明。
