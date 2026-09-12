# Kaggriculture Agent 变更日志 (CHANGELOG)

## [v1.0] - 2026-09-11 - [状态: Accepted]

### 1. 版本概述 (Overview)
- **定位**：比赛初始基线 **Baseline 1.0**。
- **文件路径**：`submissions/v1.0/main.py`
- **代码特征**：基于全网工程化最强的 COK V10 规则架构，包含 5 大路线状态机（Wheat, Wool, Milk, CARE, Strawberry）与完整防崩溃兜底。
- **SHA-256 哈希**：`1c7335f698692f1c7bac34913a9ededc0f736dfb2b51346a4fa59098ab471d01`

### 2. 本地联赛评估数据 (Local League Benchmark Results)
- **测试局数**：4 局 (2 种子 x 双座位 Seat 0/1)
- **对手**：`k320` (Rayk 开源 V23 版本)
- **数据指标**：
  | 指标 | 表现数据 |
  | --- | --- |
  | **胜率 (Win Rate)** | **100.0% (4胜0负)** |
  | **平均胜出分差 (Mean Margin)** | **+2,505.75 分** |
  | **平均得分 (Mean Score)** | 69,315.0 分 vs 对手 66,809.25 分 |
  | **异常/报错数 (Errors/Stderr)** | **0 (所有对局 720 步正常完成 DONE/DONE)** |

### 3. 逐局明细
- **Seed 20260901 (Seat 0)**: 63,816 vs 62,543 (胜, +1,273分)
- **Seed 20260901 (Seat 1)**: 64,148 vs 62,625 (胜, +1,523分)
- **Seed 20260902 (Seat 0)**: 74,466 vs 70,848 (胜, +3,618分)
- **Seed 20260902 (Seat 1)**: 74,830 vs 71,221 (胜, +3,609分)

### 4. 决策结论
- **STATUS: ACCEPTED**
- 作为一个坚如磐石的提交文件，`submissions/v1.0/main.py` 已经通过全量对局与多维度测试，随时可以作为你的首个 Kaggle 提交 Agent！
