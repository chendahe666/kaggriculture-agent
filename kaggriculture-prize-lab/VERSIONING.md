# 版本记录与恢复

目标仓库：https://github.com/chendahe666/kaggriculture-agent

研究代码在仓库的 `kaggriculture-prize-lab/`。用户明确允许覆盖原代码，因此仓库根 `main.py` 更新为当前线上同款 COK V10，与本目录 `submissions/v1.0/main.py` 完全相同；原 V4.2 可从 `c7bbcd6` 恢复。K320 历史版在 `candidate/main.py`。研究候选均在 `experiments/`，目前没有新候选通过发布门禁。

## 每轮必须留下什么

1. 开轮：在对话中写假设、机制依据、方法、耦合风险、冻结的评估方案和否证条件。
2. 每个候选：单独 Git 提交，绑定代码、SHA256 和 `reports/versions/` 报告；提交正文也包含方法、结果和结论。
3. 收轮：完整结果 JSON、OPTIMIZATION_LOG、评分契约、对手来源/哈希、研究状态一起存档。成功和失败都保留。
4. 检查并推送到已确认远端；以远端提交哈希核实成功。失败时明确区分已提交与未推送。

本次是对过去已完成研究的补建档案，所有提交使用实际建档时间，不伪造实验当时的 Git 历史。旧结果原样保留；早期 spending 字段失效，经济分析以 `results/current-corpus-calibration-v2.json` 为准。历史 CHANGELOG 中“最强”“全量通过”等结论不代表最新评估，请以 OPTIMIZATION_LOG 为准。

## 本机同步

从外层工作区运行：

```powershell
py -3.13 kaggriculture-prize-lab/scripts/checkpoint_export.py
git -C kaggriculture-agent status --short
```

脚本只复制白名单文件到指定仓库的研究子目录，保持字节相同，不删除文件，不覆盖原来的根 main.py，不自动提交或上传。之后人工/AI检查差异并按候选分别提交；不要用一次不审查的 `git add .` 代替分版本记录。若以后直接在 GitHub 克隆内工作，则不需导出，也不可再用旧外层副本覆盖新的已提交工作。

## 恢复而不破坏当前工作

请告诉 AI：“读取版本记录，恢复某个提交的版本到独立目录，先验证哈希，不覆盖当前版本”。也可在仓库内执行下列命令（替换占位符）：

```powershell
git log --oneline -- kaggriculture-prize-lab/reports/versions
git show COMMIT:kaggriculture-prize-lab/reports/versions/VERSION.md
git worktree add --detach ../kaggriculture-review-COMMIT COMMIT
```

从建档开始，每个候选自包含 main.py 都可按提交恢复。中间候选提交属于研究过程快照；需要整套评测工具和全部候选时，使用轮次收尾的 checkpoint 提交，再选择目标候选路径。需要撤销已发布代码时新增 revert 提交，不强推、不重写历史。

## 复现边界

Python 3.13，`kaggle-environments==1.32.7`。从仓库根运行：

```powershell
py -3.13 -m unittest discover -s kaggriculture-prize-lab/tests -q
```

原始回放不在 Git 中；`results/public-corpus-20260911.json` 保留来源、ID 和哈希。用本机已登录的官方 Kaggle 客户端重新获取后核对哈希。不能保证未来远端仍提供每个历史回放；本机 inbox/online-replays 是补充数据档案，切勿当作可随意删除的缓存。

Igor 源码许可未确认，不分发；对手池登记其来源和 SHA256，缺失时相关对战无法完整重跑，不能静默替换成其他对手。其他许可明确的必要对手快照附原始许可与声明。完整源码和 JSON 采用 Git 不转换换行规则，避免 Windows checkout 破坏已有哈希。
