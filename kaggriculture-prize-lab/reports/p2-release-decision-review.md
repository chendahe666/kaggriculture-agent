# P2 发布决策独立审查

审查快照：2026-09-12T05:59:48.9873393Z。只读核验已有报告、门禁、运行器与本机固定官方源码；本审查没有运行比赛，没有修改门禁、候选或运行器。安全版80局重跑当时仍在进行，不提前填写其结果。

## 结论：当前不晋级，但不是外部阻塞

保留 COK、暂不提交成立。P2b 的40个同场景比较中，A/AB相对基线仅增加1个胜分，家族等权增益为+.025；改善来自同路线镜像的两次平转胜，其他四族的基线已全部获胜。金币、局部接口测试与真实文件入口通过均不能代替新hash的完整配对确认，更不能证明对未知强手或排行榜提分。[P2b结果](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/reports/p2b-20260912-report.md>)

最新用户已作“模拟证据支持后优化并提交”的条件授权；当前缺的是满足条件的证据，不是再次申请普通本地研究或获准提交的笼统权限。`research-state.json` 的历史“待方向批准”文字不能覆盖其中较新的条件授权记录。也不能把未晋级解释成“算法已穷尽”或“必须用户救场”。[当前授权与研究状态](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/research-state.json>)

## 90种子确认是否值得开

门禁v2的固定lambda混合 e 检验数学成立：对IID的有界种子块差值D，每个预先固定的非负乘积在均值非正的原假设下期望不超过1；混合仍然如此，门槛40对应一侧alpha=.025。只在固定候选、固定池、固定统计设计和独立种子假设下解释；同步跨族重抽样仅作诊断，不外推未知对手。

五族零退化、90种子的Bonferroni Clopper–Pearson上界为.04988149；89种子不够，90种子中出现1个负族块的上界约.07149104。因此本预算实际要求每族零负种子块。族块按双座位平均，单席降档可能被另一席改善抵消，仍须报告逐场降档。

主界是一侧97.5%，五族非劣界同时95%，不是联合95%置信区域；简单联合覆盖下界为92.5%。发布要求全部命题成立，是交并检验：任何一个必要命题为假时，通过所有有效分项检验的概率不超过5%。这不是“候选正确的后验概率”。[门禁实现与假设](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/scripts/paired_release_gate.py:138>)

功效有明确必要条件：由对数凹性，90块且样本均值m时，混合e值不超过 `mean_lambda[(1+lambda*m)^90]`。m=.025时上界仅4.20576，m=.05时仅25.68784；达到40至少需要样本均值>.05579018，实际离散收益可能需要更高。只有4个开发种子，不能据此精确估计确认通过概率；但当前稀疏、镜像集中的收益没有为机械投入1800局提供充分依据。90种子是可能有用的确认预算，不是必须消耗的配额，也不是普遍足够的功效保证。不得据新结果改lambda、放宽门禁或追加样本追逐显著性。[原预算及发布目标](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/reports/p2-20260912-plan.md>)

## 资源解释须分两条线

固定官方配置为actTimeout=1秒、初始remainingOverageTime=60秒。框架每步扣除 `max(0,duration−1)`；本次调用超出“1秒+剩余overage”才形成DeadlineExceeded。因此一次本地1.5秒调用不自动等于官方超时，CPU时间也不能替代官方wall duration。[官方配置](</C:/Users/chend/AppData/Roaming/Python/Python313/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.json>)、[超时判定](</C:/Users/chend/AppData/Roaming/Python/Python313/site-packages/kaggle_environments/agent.py:220>)、[overage扣减](</C:/Users/chend/AppData/Roaming/Python/Python313/site-packages/kaggle_environments/core.py:629>)

与此同时，当前门禁默认`max_call_ms_limit=1000`，是另加的严格本地上限；即使官方完成且overage尚充足，它仍可REJECT。此时应写“未通过项目保守资源线”，不能写“官方超时”。本审查不调整它，也不通过事后修改manifest上限让旧失败变PASS。运行器当前wall/CPU序列只覆盖函数内部，明确排除加载和部分框架开销；还需分别保留真实文件路径的框架duration/overage、峰值内存与依赖检查。本机通过不是线上容器保证，DONE也不证明每条工作指令没有静默无效。[本地门禁](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/scripts/paired_release_gate.py:236>)、[运行器测量范围](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/scripts/run_terminal_track.py:72>)

## 可行的本地下一步与真正需要方向的边界

1. 完成已启动的安全版80局，按新hash核对与旧版的胜分、降档、入窗状态、欠账撤销、现金guard及资源差异。复用旧对照明确标为开发，不把修复测试升级成新独立确认。
2. 执行已预注册、审查通过后最多16局的强来源开发压力测试，检验“只会改善镜像平局”这个竞争解释。同源新文件仍归原族，附加压力结果不事后改五族主权重。[P2c范围](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/reports/p2c-20260912-plan.md>)
3. 若仍无可推广的主收益，可退役这组候选的参数搜索；本地仍有具体因果问题：被肥料任务替代的小麦/草莓收益、带需求时序的有限终局价值、共同仓容与多人任务分配。先在已打开的失败场景做可证机制/小型对照，再选择是否形成下一冻结候选。P2a已证明“更深搜索未修复错误估值”，没有证明整个规划方向失败。[已记录反例](</C:/Users/chend/OneDrive/文档/ChatGPT/kaggle-agriculture/kaggriculture-prize-lab/reports/p2a-20260912-report.md>)

真正需新方向/外部条件的情况包括：显著扩展用户任务范围、改变已承诺发布标准、购买计算、突破明确预算、取得不可合法获取的数据/许可证、或修改账户/队伍等设置。单个候选平台期、少量开发局未显著、没有当前高分源码、或确认实验功效不足，本身都不是全面停止本地研究的外部阻塞。

预算应先对账：P2b已224局，加安全80局及可选强源16局为320局；再开1800确认即2120局，尚未计独立诊断/文件入口复核。原计划说“总约2100”，不能把以上宣称为仍在严格2100上限以内；任何确需扩支应先明确剩余额度和成本。本审查不扩预算。是否开确认须由冻结前的完整开发证据决定；不晋级与继续有信息的本地研究可以同时成立。

核验锚点：门禁SHA256 `8acd9877f936cda3259b2e11e305a92bfb794da9fc19f84f60e407c472536c15`；官方引擎SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`，与项目合同一致。确认912001–912090仅在计划中保留；本审查未打开任何确认场景。
