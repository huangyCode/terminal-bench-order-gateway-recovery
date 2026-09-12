# Terminal-Bench 3 面试测试题：目标理解与完成计划

记录日期：2026-09-12

## 1. 作业的本质

这不是一道要求候选人解决的普通编码题，而是一项“基准测试作者”考核：候选人需要原创设计、实现、验证并记录一套 Terminal-Bench 3 任务，最后将完整成果放入自己的 GitHub 仓库供面试方审核和复现。

面试方真正考察的是 Founding Engineer 所需的端到端能力，包括：

- 从分散文档、CI 配置和 review 规则中独立建立正确需求模型；
- 识别真实、有经济价值且适合终端完成的问题；
- 设计清晰、公平、稳定、可程序化验证的任务；
- 构建可复现的 Docker 环境、标准答案和独立 verifier；
- 熟练使用 Codex、Claude Code 和 Harbor；
- 区分模型能力失败与 API、认证、容器、超时等基础设施失败；
- 分析 Agent trajectory，解释模型为什么失败；
- 对 verifier 进行安全与防作弊审计；
- 在七天内把一个不确定项目真正收尾并交付。

## 2. 面试官的核心目标

面试官希望看到的不是“一道没人能完成的怪题”，而是以下完整证据链：

> 候选人发现了一项现实、有价值、专家可完成的计算机工作；将其转化为清晰可复现的 Terminal-Bench 3 任务；构造了可靠且不可轻易绕过的 verifier；证明标准答案能够稳定通过；证明空操作不能通过；并通过有效模型试验表明当前强 Agent 因有意义的能力缺陷而稳定失败。

他们尤其会判断：

1. 难度是否自然，而不是人为堆砌。
2. Agent 的失败是否来自真实能力边界，而不是坏题面或坏环境。
3. verifier 是否既无漏判，也不过度绑定作者的参考实现。
4. 实验是否可复现、可审计且诚实。
5. 候选人能否解释自己的设计、迭代和取舍。

## 3. 最终交付物

最终应提交一个候选人自己的 GitHub 仓库。至少包含完整任务：

```text
tasks/<task-name>/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── ...
├── solution/
│   ├── solve.sh
│   └── ...
└── tests/
    ├── Dockerfile
    ├── test.sh
    └── ...
```

仓库还应记录：

- 使用的 Terminal-Bench 上游仓库、commit SHA 和 Harbor 版本；
- 当前 CI 默认 Agent、模型、参数和 trial 数；
- 所有静态检查、rubric、Docker、Oracle 和 Nop 的命令与结果；
- 六次标准 Agent trial 的配置、状态、reward 和日志位置；
- 两次 adversarial trial 的配置与零分结果；
- 模型失败分析；
- 任务与 verifier 的迭代记录；
- 完整复现说明。

不需要向 Terminal-Bench 官方仓库提交 PR，但仍需要按照当前 TB3 CI 和 review 标准完成任务。

## 4. 硬性验收标准

### 4.1 自动检查

最终冻结版本必须满足：

- 所有 required static checks 通过；
- implementation rubric 通过；
- Docker build 通过；
- Oracle validation 获得 1.0 reward；
- Nop validation 获得 0 reward。

### 4.2 标准 Agent trials

按照最终执行时 TB3 CI 的当前默认配置运行：

| Agent | 模型 | 推理配置 | 次数 | 要求 |
|---|---|---|---:|---|
| Codex | GPT-5.6 Sol | xhigh | 3 | 三次均真实失败 |
| Claude Code | Claude Opus 5 | max | 3 | 三次均真实失败 |

“真实失败”意味着 Agent 正常启动、正常获得工作环境并进行了有效尝试，但最终产物没有通过 verifier。

以下情况不能计为模型失败：

- API、认证或 rate-limit 错误；
- Agent 进程崩溃；
- Docker、Harbor 或容器错误；
- 模型没有真正开始执行；
- 不合理 timeout 或其他基础设施故障。

### 4.3 Adversarial trials

- Codex `/cheat` 一次，reward 必须为 0；
- Claude Code `/cheat` 一次，reward 必须为 0；
- 任何非零 reward 都表明 verifier 存在可利用路径，必须修复并重新验证。

### 4.4 配置的权威来源

邮件示例不是最终权威。正式运行时必须重新检查当前仓库中的：

- `.github/harbor-run-defaults.yml`；
- CI workflows；
- `TASK_REVIEW_AUTOMATION.md`；
- `REVIEWING.md`；
- static check scripts；
- implementation rubric。

## 5. 任务边界

### 合格任务应当具备

- 现实世界价值：确实有人会付费请专业人士完成；
- 明确输入、输出和成功条件；
- 可通过终端完成；
- 人类专家在合理时间内可完成；
- 可进行确定、程序化、独立验证；
- 允许不同的合法实现方式；
- 对时间和符合声明要求的硬件稳定；
- 难度来自长链条推理、环境探索、跨组件一致性、迭代调试或领域约束。

### 不合格或高风险做法

- 使用隐藏要求或模糊题面制造失败；
- 依靠断网、缺工具、坏环境或不合理超时制造难度；
- 设计冷知识谜题、随机大计算或纯粹人为复杂度；
- verifier 只接受参考答案的具体实现方式；
- 测试覆盖不足，使表面产物能够通过；
- 将 ground truth、测试或标准答案泄露给 Agent；
- 将 API、容器或认证故障记录为模型失败；
- 修改任务后继续引用旧 commit 的 trial 结果；
- 为迎合特定模型的弱点不断加入无现实意义的陷阱。

## 6. 正确的任务设计方法

推荐设计链路：

```text
真实工作问题
    ↓
定义客观成功状态
    ↓
证明人类专家可解
    ↓
设计独立 verifier
    ↓
识别任务天然存在的模型能力瓶颈
    ↓
运行 Agent 并分析真实失败
    ↓
修复题面、环境或 verifier 缺陷
```

优先选择包含两至三个自然难点的任务，例如：

- 探索陌生或有状态的系统；
- 跨多个文件、组件或服务维持一致性；
- 从噪声或不完整材料中推断规则；
- 需要反复运行、观察、修正；
- 局部正确但容易破坏全局不变量；
- 同时满足正确性、兼容性和性能约束；
- 存在多个看似合理但语义错误的实现路径。

## 7. 完整执行计划

### 阶段 0：冻结基线

记录上游仓库 URL、commit SHA、Harbor 版本、Docker 版本、CI workflow、rubric 版本以及当前 Agent 默认配置，确保后续结果可以对应到唯一基线。

### 阶段 1：建立合规矩阵

完整阅读 Contribution Call、Contributing Guide、proposal rubric、implementation rubric、CI/review 文档、默认 Agent 配置和静态检查脚本。查看若干已经通过 review 的高质量任务。

建立 checklist；每项包含要求来源、实现方式、验证命令和证据位置。

### 阶段 2：评估三个候选题

每个候选题写清：

- 现实使用者和业务价值；
- 输入环境与预期产物；
- 客观成功条件；
- 专家解法；
- Agent 可能失败的位置；
- verifier 设计；
- 潜在作弊路径；
- 七天内完成成本。

根据现实价值、可验证性、自然难度、防作弊能力和交付风险选择一个，而不是实现第一个想到的题。

### 阶段 3：先做可行性原型

在正式完善任务前证明：

1. 环境可稳定构建；
2. 作者本人能够完成任务；
3. verifier 能区分完整正确答案与错误答案。

至少测试：空产物、部分产物、格式正确但语义错误的产物、hard-coded 假答案和篡改辅助文件的尝试。如果无法可靠验证，应尽早换题。

### 阶段 4：正式实现

推荐顺序：

1. 写成功条件；
2. 写 verifier；
3. 写 Oracle；
4. 写环境；
5. 最后精炼 instruction。

这样可以减少 instruction 和 tests 不一致的风险。

### 阶段 5：本地质量验证

完成并记录：

- 静态检查；
- Docker build；
- Oracle；
- Nop；
- implementation rubric；
- 人工负向测试；
- verifier 攻击测试；
- Oracle 重复运行和确定性检查。

### 阶段 6：开发性 Agent 试跑

先运行低成本或单次开发试验，检查：

- instruction 是否有歧义；
- 环境是否缺少合理必需工具；
- 输出路径是否清晰；
- timeout 是否公平；
- verifier 是否误杀合法实现；
- 任务是否明显太简单。

开发试跑不能替代最终六次正式 trial。

### 阶段 7：最终标准 trials

冻结任务 commit 后完成 Codex 三次和 Claude Code 三次。每次记录：Agent、模型、参数、版本、commit、时间、reward、运行状态、日志位置、是否为有效失败、失败阶段和根因。

如果模型通过，应先判断是任务太简单、环境泄露、测试不足，还是模型找到了合法的更优解。只能通过保持现实性的方式改进任务。

### 阶段 8：Adversarial trials

分别完成 Codex 和 Claude Code 的 `/cheat`。重点审计：tests/Oracle 泄露、verifier 篡改、reward 伪造、artifact 路径利用、预计算常量、测试覆盖缺口、sidecar 和权限边界。

发现漏洞后，需要修 verifier，并重跑 Oracle、Nop 及所有受修改影响的正式试验。

### 阶段 9：失败分析

每类失败按以下结构分析：

```text
失败现象
→ Agent 的关键决策
→ 决策为什么看似合理但实际错误
→ verifier 如何捕获
→ 是否为两个模型共有模式
→ 是否可能来自题目歧义或环境问题
→ 为什么这是有研究价值的能力缺口
```

### 阶段 10：仓库审计与交付

确认所有结果对应最终 commit；清除 API key、OAuth token、登录信息和 shell history；从干净环境按 README 复现关键检查；推送 GitHub 并确认面试方有权访问。

## 8. 七天安排

| 日期 | 目标 |
|---|---|
| 第 1 天 | 阅读规范、冻结基线、建立 checklist、提出并选择候选题 |
| 第 2 天 | 构建最小环境、正确答案和 verifier 原型，证明可行性 |
| 第 3 天 | 完成 task 目录、Docker、Oracle、tests 和 instruction |
| 第 4 天 | 通过静态检查、rubric、Docker、Oracle、Nop 和防作弊审计 |
| 第 5 天 | 开发试跑并开始正式 Codex/Claude trials，分析结果 |
| 第 6 天 | 冻结最终版本，补齐 3+3 标准 trials 和 1+1 cheat trials |
| 第 7 天 | 完成失败分析、复现审计、凭据清理、README 和 GitHub 提交 |

正式 Agent 单次可能运行较久，因此不能把试跑推迟到最后一天。

## 9. 主要风险与控制办法

### 风险一：模型至少成功一次

招聘要求是六次全部真实失败。控制方法是尽早完成可运行原型，给试跑和有原则的迭代预留至少两天。

### 风险二：零分来自基础设施故障

逐次检查运行状态、trajectory、耗时、Agent 实际行为和最终 verifier 结果。异常试验必须重跑。

### 风险三：verifier 只认可 Oracle

为 verifier 构造至少一个与 Oracle 实现不同但语义正确的替代答案，并确保也能通过。

### 风险四：任务说明与测试不一致

将 instruction 中每项要求映射到具体测试；将每个测试映射回明确的题面要求。

### 风险五：修复后结果失效

任何影响 instruction、environment、solution、tests 或 task 配置的修改，都应评估并重跑受影响的验证。正式报告中的全部核心结果应对应同一最终 commit。

### 风险六：泄露凭据或标准答案

在提交前执行 secret scan，并确认 Agent 容器无法访问 tests、Oracle、ground truth 或宿主机凭据。

## 10. 面试准备

应能够清楚回答：

- 为什么这个任务有现实价值？
- 难度具体来自哪里，为什么不是人为陷阱？
- 人类专家需要多久？
- Oracle 使用了什么策略？
- verifier 如何支持不同合法实现？
- 如何证明六次失败不是环境问题？
- 两个模型各自在哪个决策点失败？
- `/cheat` 测试了哪些攻击面？
- 曾发现并修复过哪些 verifier 漏洞？
- AI 工具参与了哪些工作，关键判断由谁完成？
- 如果有更多时间，会改进什么？

## 11. 最终完成定义

> 在固定、可复现的 Terminal-Bench 3 版本上，交付一道原创、现实、有价值、专家可解且程序化可验证的终端任务；最终冻结版本通过全部静态、rubric、Docker、Oracle 与 Nop 检查；Codex GPT-5.6 Sol xhigh 和 Claude Opus 5 max 各三次正常试跑均因有意义的模型能力不足而失败；两个 adversarial trial 均获得零分；GitHub 仓库提供完整、可审计的配置、命令、结果、日志索引和失败分析。

完成优先级为：

```text
选题质量
→ verifier 可靠性
→ Oracle 可复现性
→ 模型真实难度
→ 防作弊能力
→ 实验记录
→ 仓库展示
```
