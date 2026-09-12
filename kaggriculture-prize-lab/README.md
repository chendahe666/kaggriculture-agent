# Kaggriculture Prize Lab

这个目录用于在公开、可复现、符合竞赛规则的前提下，研究并改进 Kaggriculture 智能体。

## 最新阅读入口（2026-09-11）

请优先阅读 **WORKFLOW.md**（完整 pipeline、评价指标、人机操作指南）、
**GAME_RULES.md**（官方源码规则）、**OPTIMIZATION_LOG.md**（每轮实验及结论）、
**PIPELINE_PROMPT.md**（项目主流程提示词）和 **research-state.json**（续跑状态）。

最新主研究底座为用户重复提交的 **COK V10**（56156204 / 56156051），不是下方历史段落中的 K320。
K320 原始文件保留不动，用作历史控制组。本轮市场组合版未通过发布门槛，没有提交。
已自动下载最新连续 20 场本方对局和前五名涉及的 8 场去重回放；正确性已逐帧校准。
下面的当前结论/推荐动作是 9 月 2 日历史记录，以上述新文档为准。

## 当前结论

- `candidate/main.py` 是当前候选基线：Rayk 当前公开产物 V23，内部版本标识为 `K320-adaptive-rank1-no-late-seed`。
- Rayk Notebook 的历史公开最好成绩为 2990.4（V11），但当前下载的 V23 页面成绩是 2563.4；二者不是同一个产物。
- `public-baseline-v10/` 是 COK-ZhangZiliang 的公开 V10 仓库快照，包含测试、联赛脚本和策略文档。
- 当前候选对 COK V10 的小型双座位联赛为 0 胜 8 负，平均分差 -1487.25。它还不适合直接提交，更不应把单一榜单分数当作绝对强度。
- 三个简单消融版本均弱于原始 K320，因此暂时保留原始 K320 作为候选基线。

## 目录说明

- `candidate/`：准备继续优化的候选智能体。
- `public-rayk-k320/`：Rayk 当前公开产物的原始副本与来源说明。
- `public-baseline-v10/`：COK V10 公开仓库快照。
- `experiments/`：候选变体和消融实验。
- `results/`：机器可读的联赛结果。
- `RESEARCH.md`：公开高分方案与策略研究。
- `RESULTS.md`：本地验证结果。
- `ROADMAP.md`：下一轮优化路线和晋级门禁。

## 复现实验

上游 COK 项目指定 Python 3.12.13；本机使用 Python 3.13 和 `kaggle-environments==1.32.7` 也已完成验证。

在 `public-baseline-v10/` 中运行：

```powershell
py -3.13 -m pytest -q
py -3.13 scripts/run_league.py --help
```

先用固定训练种子调参，再用从未参与调参的留出种子复核。任何版本必须同时测试两个座位，不能使用种子身份、私有状态或对手身份硬编码。

## 当前推荐动作

不要直接提交当前候选。先扩充对手池，再针对公开可观测状态优化路线选择、市场售卖时机、行动利用率和终局清仓；只有通过 `ROADMAP.md` 中的门禁后，才生成提交包。
