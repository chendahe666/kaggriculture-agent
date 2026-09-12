# P2：对手来源与验收审查

2026-09-12 UTC；本文件是本轮方法审查，不是新的比赛成绩。

## 为什么继续搜索独立方法

旧公开对手中，同路线文件不能算多个独立家族。新研究实际检查了动态多工人调度、单农夫经济、分区任务队列以及标为强化学习的实现；按真正执行代码而非标题分类。五个家族目前是人工保守分类，并不等于五类强手。

|来源|实质方法与处置|许可/获取记录|
|---|---|---|
|[Deepesh](https://github.com/deepeshumrao/kaggriculture-agent/blob/main/deliverables/kaggriculture_submission.py)|单农夫小麦优先的响应式贪心；纳入低供给控制，不能代表前排强手|MIT；首轮未记精确下载起止，使用明确标注的文件时间代理|
|[Maverick V1](https://www.kaggle.com/code/maverickss26/kaggriculture-v1)|分区、持续任务、动态雇工、纯种植经济；纳入第五个暂定行为家族|Apache-2.0；2026-09-12T05:21:37.9577099Z至05:21:40.7464473Z，版本1/1；完整源码审阅，仅去掉Notebook写文件magic，未运行整个Notebook|
|[Alejandro PPO](https://www.kaggle.com/code/alejandrofonda/kaggriculture-ppo-training)|检查实际代码发现网络售卖输出未用于行动，更新缺PPO比率/裁剪，对照“random”实际上PASS；不按标题称为成熟PPO强手|Notebook Apache不覆盖单独数据集代码/权重；后者许可unknown，未导入或加载权重，排除|
|[Pilkwang](https://www.kaggle.com/code/pilkwang/kaggriculture-structured-economic-policy)|本次取得的最新版本实际沿用固定路线，不把旧文章中的动态策略描述套到当前源码，不增加独立家族|旧指定版本访问失败，不绕过访问限制|
|Vijai modular / Avik microeconomic|实际为单农夫种植型规则，未发现其标题暗示的额外学习能力；与低供给控制覆盖重叠|仅审阅，不纳入正式池|

Maverick源码SHA256 `7ae4354862f4674155b788526e442da8edcf0dbe57cee808fed9fb629e0c0fa8`；原Notebook SHA256 `6b413ab926685074bc7044a1de752c2af288366771f1539eeb511558b176bd5b`。公开候选出处、固定文件及许可见`opponent-pool-p2.json`和对应public目录。历史Notebook分数不充当本次下载文件的成绩；没有查到的采集排名、分数保持未知，不补造。

完整只读下载审查记录保存在本机`inbox/opponents/fifth-family-source-audit-20260912.json`（SHA256 `6dd5feefd2e04e26950d411ee47ae7506471545f2588e7942a92724d3d65752d`），含其他排除来源及失败访问。该记录不含登录凭据。公开档案不携带许可未明确的代码、模型权重、原始对局或书籍全文。

## 评分器的纠错，不是为候选改分

稀疏反例：种子块配对胜分差D有10%概率为+.1、1.5%为−1、其余为0，真实均值为−.005。90个样本可能没见到罕见损失，普通bootstrap却给出正下界。这说明经验方差很小不等于真实风险很小。

在确认集尚未打开时，`paired_release_gate.py`升级v2：固定混合e检验为正式均值门，bootstrap仅作近似诊断；保留原目标和90种子预算。19项门禁单测包括这个反例。数学条件、lambda、alpha、家族CP边界已写入P2预注册。单测验证实现和反例，不证明竞赛评测具有现实代表性。

这一保守门有明确功效代价：90块、样本均值+.025时，固定混合e的理论上界约4.206，低于40；即便+.05，上界约25.688。由log(1+lambda D)凹性可得，达到40所需样本均值至少约+.05579，稀疏结果往往要求更高。因此，不应在开发改善只来自少数镜像平局时机械投入1800次对局，更不能事后放宽门禁制造“验证通过”。

资源也要区分：本地最大单步超过1秒不自动等于官方超时，引擎还扣减60秒初始overage；旧本地1秒严格线是额外保守检查。真实文件加载、框架逐步时长与剩余overage另做验证。本机运行不等于线上容器CPU/内存保证。

## 可用于下一轮的狭义经验

1. 改算法后同时测试真正提交入口；直接调用指定函数可能掩盖加载错误。本次Python字典键重定义不改变插入位置，官方最后callable选择了帮助函数；旧失败文件保留，新文件使用最后追加的独立入口。
2. 交货、售出和价格反馈必须拆开归因；更早到仓不代表应更早卖出。对手历史无产出来源的证明、不可买商品、已知NPC需求、容量和融资边界须一起成立。
3. 评估研究价值包括“这批数据能否改变决定”；五个弱/同路线控制的样本量增加，不能填补未知强手的策略覆盖。

这些仍是本项目local evidence与方法约束，未推广为跨比赛实证规律，未修改底层模型权重。通用skill仍为0.1.1；本轮新增证据先保存在项目中，后续独立情境验证后再考虑扩大技能记忆范围。

## P2c 当前公开来源追加审查

[Arlene](https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised)：官方CLI获取完整Python输出于2026-09-12T05:51:39.0098318Z至05:51:43.8933445Z，32456字节，SHA256 `d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4`。与Notebook内嵌文本逐字节匹配；审阅副本只多一个结尾换行。公开页面version ID347020472与本地内容hash分开保存；显式版本请求403且CLI输出下载忽略version参数，不假称成功固定API版本。

两条719步表仅360–431不同，step360按公开商店/市场/种植选路，每72步作现金保护。标准库＋常量JSON解压，两人完整审阅，没有外部文件/网络/进程/动态库/任意执行。动作与当前COK的12表仅2/719整步相同，不是逐步复制，但不证明祖先独立，仍按路线大类压力测试。Notebook声明Apache-2.0，未交代“supplied C++”动作带上游署名，因此代码不打包、不再发布；Git仅保留来源及派生评估。原版/安全联合版各8场实际均全负，不能用索引2703.9等互相冲突的评分快照代替下载文件的实测。

[Reyhan](https://www.kaggle.com/code/reyhanksatria/adaptive-route-agent-v2)：官方CLI Notebook获取于2026-09-12T05:45:32.2059193Z至05:45:33.4952841Z；页面version ID346986658。核心agent.so927424字节、SHA256 `d3b4e19dfd20f1d9b229d1d15cab9ee20068d100fb99fcf4c44051d59fb174ea`，没有对应源码/构建谱系。只检查文本包装器和归档成员，二进制没有提取、加载或执行，拒绝纳入对手池。高分和Notebook许可证不能补上这个安全证据缺口。

本机完整ledger：`inbox/opponents/strong-source-audit-20260912/audit-manifest.json`；公开复现时可自行从上述来源获取并校验hash，不匹配就注册新版本，不能冒用旧成绩。当前日期后源码/评分变化均不覆盖本次采集快照。
