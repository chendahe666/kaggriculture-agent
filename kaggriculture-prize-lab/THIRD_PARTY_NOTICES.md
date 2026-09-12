# 研究档案第三方来源与修改声明

- `public-baseline-v10/main.py`、`submissions/v1.0/main.py` 为 COK-ZhangZiliang/Kaggriculture 的原始 COK V10 快照。Apache-2.0 许可及完整原声明保留在 public-baseline-v10/。`experiments/track-market-20260911/*/main.py` 是本项目 2026-09-11 修改版：在原控制器后追加市场订单排序、需求恢复补售、库存投影或公开状态门控，具体区别与哈希见 manifest.json、overlay.py、gate_overlay.py 及逐版本报告。不是原作者验证的版本。
- `candidate/main.py` 是 Rayk 公开 V23/K320，来源见 candidate/SOURCE.md。其他 K320 experiments 为本项目修改版；禁用抢售、禁用路线反制或修改抢售窗口/排序，具体补丁见 experiments/ 文档与 manifest。原授权与声明见 submissions/k320-v23-current-20260902/THIRD_PARTY_NOTICES.md 和 LICENSES/Apache-2.0.txt。
- `public-seyam-v21/` 保留 MIT 许可和嵌入式 Apache-2.0 策略声明。`public-lonespear/` 保留 MIT 许可；仅归档本轮使用的四份单文件策略，不包含完整上游仓库。
- `official/` 来自 Kaggle/kaggle-environments（Apache-2.0），保留原始引擎/schema/说明字节，版本 1.32.7。适用许可文本见 licenses/Apache-2.0.txt；源码哈希见 evaluation-contract.json。
- Igor 策略许可未确认，仅保留公开来源和哈希，不分发代码或 Notebook。原始回放不上传。

上述许可作用于各自来源内容，不将本项目其余内容或比赛回放自动重授权。
