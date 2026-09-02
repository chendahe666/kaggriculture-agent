# Kaggle 提交后人类侧报告协议

此协议自 2026-09-02 起生效，持续到用户明确修改。

每次上传 Kaggle 后，在本目录创建一份文件：

```text
YYYY-MM-DD_<version-or-submission-id>.md
```

如果刚上传时仍为 `Pending`，先写已知事实和待补证据。服务器 validation、
Replay、Agent logs、Episodes 或 rating 更新后，继续更新同一文件，保留时间线。

## 必填：Human-side validation report

- 提交时间、版本、commit、文件 SHA256、submission ID 和描述。
- 本地实际执行的测试、环境版本、seeds、对手和双方位置。
- Episode 完成率、最终状态、异常、返回结构错误和运行时间。
- Kaggle validation 状态，以及 Replay / Agent 0 / Agent 1 logs 的检查结果。
- 明确区分单局最终金币与 Kaggle 技能评分。
- 未验证、不可见或仍在等待的项目必须标为未知，不得推测成通过。

## 必填：Optimization report

- 相对上一线上版本只改变了什么。
- 该改变要验证的单一假设。
- 相同条件下的配对结果：中位数、最差值、胜率和逐条件差值。
- 最差三局及第一次错误决策。
- 新风险、可能的 leaderboard overfitting 和尚未覆盖的场景。
- 下一轮只能给一个结论：`promote`、`hold` 或 `reject`。

## 必填：五分钟自然语言说明

使用不要求读者理解代码的中文，按以下顺序说明：

1. 这次做了什么。
2. 为什么只做这个改变。
3. 本地和 Kaggle 实际验证了什么。
4. 哪些结果看起来更好，哪些仍然不知道。
5. 下一步建议以及人需要做的决定。

避免粘贴大段代码、原始日志或只有开发者才懂的缩写。必要的技术词在第一次
出现时用一句中文解释。

