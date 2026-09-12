# COK V10 当前基线建档

建档：2026-09-11。用户授权覆盖原根代码；不是新优化候选的晋级。

- 来源：COK-ZhangZiliang/Kaggriculture，原许可和第三方声明已保留。
- SHA256：`1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`。
- 路径：仓库根 main.py；研究目录 submissions/v1.0/main.py 与 public-baseline-v10/main.py 为相同字节。
- 线上关联：56156204 / 56156051，用户确认重复提交。此前 K320 的 55965192 不属于本版本。
- 选择依据：开发闭环 K320 对 COK 0/8；当前 20 场线上回放 7/0/13，并非充分强度证据。已有完整研究结果见 OPTIMIZATION_LOG。
- 本次归档核验：24 个机制/评价单元测试通过；兼容后的根 test_local.py 在 seed 20260901 对 starter，720 状态，719 调用，DONE/DONE，动作形状错误 0，外部未捕获异常 0，金币 179053 对 3632。内部吞掉的异常无遥测接口，计数 unavailable，不当成 0。
- 另行按实际文件路径运行 `env.run(['main.py', 'starter'])`，同 seed，720 状态，DONE/DONE，金币一致。这是加载/运行烟雾测试，不是榜单强度评估。
- 原 V4.2 保留于 Git c7bbcd6。原 logs/episode_001.log 未覆盖，新日志为 logs/cok_baseline_20260911.log。
- 本次没有新 Kaggle 提交；市场 integrated 否决，gated 仅研究保留。

唯一建议：**hold**（保留当前基线与回退点，不宣称本次带来提分）。
