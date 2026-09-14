# 执行计划与 reviewer 视角评审

制定时间：2026-09-14（Asia/Shanghai）
目标：9-15 之前完成全部阻塞项、冻结任务、跑完 6 次标准 trial + 2 次 cheat trial、交付仓库。
基线：上游 `harbor-framework/terminal-bench` @ `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`，Harbor 0.18.0。

---

## 第一部分：以 reviewer 身份对当前版本的评审结论

评审依据：`docs/prompts/task-implementation.toml`（35 条）、`.github/workflows/static-checks.yml`（22 条）、
`CONTRIBUTING.md`、`docs/TASK_REVIEW_AUTOMATION.md`，以及已合并任务 `tasks/risk-scorer-replay` 的实际写法。

### 判定汇总

| # | rubric 条目 | 判定 | 依据 |
|---|---|---|---|
| F1 | `difficult` | **FAIL** | Codex 在 V2c/V3a/V3b/V3c 四个版本全部 reward 1.0 |
| F2 | `deterministic_reproducible` | **FAIL** | V3d Oracle 两次 5-run：3/5+1err、0/5 |
| F3 | `test_instruction_alignment` | **风险** | `tests/test_gateway.py` 527 行 / 15 case，rubric 期望 ~100 行 |
| F4 | `instruction_concision` | **风险** | instruction 第二段是 8 分句的分号清单，等于测试清单 |
| F5 | `task_toml_schema` | **FAIL** | `author_name`/`author_email`/`[task].authors` 仍是 TODO |
| F6 | 三条 `*_explanation_quality` + `task_readme` | **FAIL** | README 四段全是 TODO |
| F7 | `verifier_execution_isolation` | **风险** | `stderr=PIPE` + 阻塞 `.read()`；无 cheat oracle |
| F8 | 自定原则（infra≠模型失败） | **FAIL** | `test.sh` 预写 reward 0，verifier 内部 infra 错误被洗成可计分 0 |
| F9 | `no_extraneous_files` / `environment_hygiene` | **风险** | `tests/__pycache__` 曾进入 staging |
| F10 | `expert_time_estimate` | **风险** | 仍是 4.0，与当前七层难度不符 |
| — | `verifiable` `solvable` `interesting` `novel` `agentic` `outcome_verified` `task_security` `separate_verifier_configured` `ctrf_reporting` `binary_reward` `artifact_efficiency` `structured_data_schema` `solution_quality` `category_and_tags` `task_name` `resource_configuration` | PASS | 已核对实现 |

### F1 根因分析（最重要的一条）

不是"场景不够多"，而是**难度的种类错了**。两个结构性原因：

1. **题目本身是一份完整规格。** `instruction.md` 把 8 条不变量全部列出，`protocol.md` 给出全部语义。
   对前沿 agent 来说这是"照规格实现"，配合 8 小时预算和可反复运行的环境，属于它最强的工作类型。
2. **题目允许把并发折叠成串行。** 证据是 D5 中 Codex 交付的 artifact：

   - `store.py:267` `sync_lock()`：`fcntl.flock(fd, LOCK_EX|LOCK_NB)`，注释明写
     "flock is released by the kernel if a process is killed, avoiding a stale database lease"。
   - `core.py:705`：这把锁**只包住网络 reconciliation**，意图落盘走 SQLite `BEGIN IMMEDIATE`，不需要它。

   拿这个实现去对 V3d 的十条 barrier：worker B 在 A 等 I/O 时仍能落盘意图（意图不走锁，已满足）；
   SIGKILL A 后锁由内核释放（Codex 注释正是冲着这个写的）；B 接管后先 REPLAY 歧义前缀再发新 suffix
   （V3a 的 `acceptance_known` + 有序 outbound recovery，已满足）。

   **结论：V3d 大概率同样会被 Codex 通过。** `codex-v3d-calibration` 仍应照跑（$2 / 约 45min，是正式报告的证据），
   但不能作为"继续加第 8 个场景"的决策依据。

---

## 第二部分：V4 难度轴变换设计

### 设计目标

让"单协调者折叠"这条路在规则层面不成立，制造一个**安全性与活性互斥**的两难，
使得任何不做 fencing 的设计必然在两个闸中至少挂一个。

### 协议增量（只加一个概念）

venue 对每个 session 维护 `epoch`。请求携带 `epoch`。venue 拒绝 `epoch` 低于当前值的请求，
返回 `STALE_EPOCH` 且不产生业务效果。gateway 接管会话时必须先持久化并递增 `epoch`。

语义完整写入 `protocol.md`，无隐藏规则。

### 两个互斥闸

**闸 A（活性）：** verifier 让 venue 把 worker A 的响应挂住 T 秒，同时要求 worker B 在有界时间内
完成它自己那批订单的 sync。
→ 全局阻塞锁直接死：A 没死、仍持锁，B 永远拿不到。**废掉 flock 方案。**

**闸 B（安全）：** A 不是被 SIGKILL，而是 **SIGSTOP 冻住**；B 靠租约超时接管并完成恢复；
然后 **SIGCONT 唤醒 A**，A 手里那个 in-flight 请求会照原样发出。要求 venue 侧无第二次业务效果。
→ 纯租约超时方案死：内核不会撤销一个被冻住又醒来的进程的写权限。**废掉租约方案。**

两闸同时要过，唯一出路是持久化 epoch + venue 侧 fencing。这是 Kleppmann 分布式锁那篇文章的核心论点，
也是 Kafka producer epoch、FIX 单会话所有权在生产中存在的原因——**不是人为陷阱，是这个岗位的核心知识**。

### 配套两项改造（同时修 F3/F4）

1. **测试重构为种子驱动的交织枚举。** 用紧凑的场景 DSL + seed 表替代 15 个手写 case：
   在协议事件边界上系统枚举断点/重排/重投组合，每个 seed 都要过。
   效果：行数下降（解 F3）；"happy path + 补丁"式实现必然在某个 seed 上崩（抗 grind）。
2. **instruction 去清单化。** 不变量搬进 `protocol.md`（保持完整权威），instruction 只声明
   "按 `/app/docs/protocol.md` 修复，该文档列出故障类别与判定口径"。
   公平性不变（规格完整），但 agent 必须自己从规格推导测试面（解 F4，且抬高难度）。

### 预期的模型失败模式（用于失败分析）

- 用 flock / 心跳租约当互斥，不做 fencing → 闸 B 出现重复业务效果。
- 为过闸 B 而把锁改成阻塞式或加长租约 → 闸 A 超时。
- 只在内存里维护 epoch，不持久化 → 重启后回退到旧 epoch，被 venue 拒绝或产生重复效果。
- epoch 递增与意图落盘不在同一事务 → 崩溃窗口内丢失 epoch。

---

## 第三部分：执行计划

### P0：外部阻塞项（需要用户本人操作，两项都是前置）

| 编号 | 事项 | 操作 | 为什么阻塞 |
|---|---|---|---|
| U1 | Claude Code 未认证 | 终端执行 `claude setup-token`，token 不要贴进对话 | 卡住 3 次正式 Claude trial、`harbor check` rubric、1 次 Claude cheat |
| U2 | Docker 内存只有 8.3 GB | Docker Desktop → Settings → Resources，内存提到 28–30 GB 后重启 | 单 trial 需约 5 GB；6 并发需约 30 GB。宿主机 36 GB 够 |
| U3 | GitHub PAT 已泄露 | 去 GitHub revoke 之前那个 `ghp_` token | 安全 |
| U4 | 署名信息 | 提供 README/task.toml 要用的姓名与 email | `task_toml_schema` |

### P1：修复与实现（我执行）

| 编号 | 事项 | 验收标准 |
|---|---|---|
| T1 | 确认 V3d 断言修复已落地，重跑 Oracle 稳定性 | `-k 10`，10/10 reward 1.0，0 exception |
| T2 | `test.sh` 区分 infra 错误与功能失败：pytest rc∈{0,1} 才写 reward，其他 rc 不写 reward 并以非零退出 | 人工注入 venue 启动失败，确认不产生可计分 0 |
| T3 | 子进程 stderr 改为临时文件，消除 daemon 化孙进程挂死 verifier 的路径 | 注入 daemon 化 artifact，verifier 不挂死 |
| T4 | 实现 V4：venue epoch + fencing，闸 A（活性）与闸 B（SIGSTOP/SIGCONT 安全） | Oracle 通过，两个已知错误实现（纯 flock / 纯租约）各挂对应闸 |
| T5 | 测试重构为 seed 驱动交织枚举 | 行数显著下降，Oracle 在全部 seed 上稳定 |
| T6 | instruction 去清单化，不变量迁入 protocol.md | 每条测试断言可追溯到 protocol.md 的明文要求 |
| T7 | 补 `task.toml` 署名、`expert_time_estimate_hours` 按真实难度上调 | 与 difficulty explanation 自洽 |
| T8 | 按 `risk-scorer-replay` 的格式补 README（Task Metadata 块 + 四段），四段由我起草、**你本人改写签字** | 四条 rubric 可过 |
| T9 | 加 `.gitignore` / staging 清理，杜绝 `__pycache__` 等 | `no_extraneous_files` |
| T10 | 可选：加 `cheat/solve.sh` 确定性 cheat oracle（daemon 化伪 artifact 必须得 0） | rubric 明确推荐，且是 /cheat 的自证 |

### P2：冻结前全量验证（我执行）

| 编号 | 命令 | 验收 |
|---|---|---|
| V1 | `for c in scripts/checks/check-*.sh; do bash $c tasks/order-gateway-recovery; done` | 22/22 |
| V2 | `harbor run -p tasks/order-gateway-recovery --agent oracle --env docker --yes -k 10 -n 2` | 10/10 = 1.0 |
| V3 | `harbor run -p tasks/order-gateway-recovery --agent nop --env docker --yes` | 0.0 |
| V4 | `harbor check tasks/order-gateway-recovery -r docs/prompts/task-implementation.toml` | 35 条无 FAIL（依赖 U1） |
| V5 | 两个已知错误实现的负向测试 | 各自挂在预期的闸上 |

全部通过后 **commit 并打 tag 冻结**，之后只改文档。

### P3：正式试跑（冻结后）

并发策略：两个 job 同时起，各 `-k 3 -n 3`，共 6 个并发容器（依赖 U2）。

```bash
# Codex 3 次
harbor run -p tasks/order-gateway-recovery \
  --agent codex --model openai/gpt-5.6-sol \
  --env docker --yes \
  --ae CODEX_FORCE_AUTH_JSON=1 \
  --ak reasoning_effort=xhigh \
  --agent-setup-timeout-multiplier 3 \
  -k 3 -n 3 --job-name formal-codex-v4

# Claude Code 3 次
harbor run -p tasks/order-gateway-recovery \
  --agent claude-code --model anthropic/claude-opus-5 \
  --env docker --yes \
  --ae CLAUDE_FORCE_OAUTH=1 --ae CLAUDE_CODE_OAUTH_TOKEN=<token> \
  --ae CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 \
  --ak reasoning_effort=max \
  --agent-setup-timeout-multiplier 3 \
  -k 3 -n 3 --job-name formal-claude-v4
```

逐次记录：agent、模型、reasoning、commit、起止时间、reward、exception、trajectory 路径、
**有效性判定**（是否真实模型失败）、失败阶段、根因。

任一 trial 出现 API/认证/容器/setup timeout → 判无效并重跑，不计入。
任一 trial reward 1.0 → 该版本不合格，回到 P1 继续提高真实难度（这会突破 9-15，需要你决策）。

### P4：对抗试跑

```bash
# 在两个 agent 的 instruction 前置 docs/prompts/hack-trial-prompt.md，各跑 1 次
```
两次 reward 必须都是 0。非零即说明 verifier 可绕过，必须修 verifier 并重跑 P2、P3 中受影响的项。

### P5：分析与交付

| 编号 | 事项 |
|---|---|
| D1 | `harbor analyze <job-dir> -m sonnet -r docs/prompts/trial-analysis.toml --job-prompt docs/prompts/trial-analysis-job.txt` |
| D2 | 按"现象→关键决策→为何看似合理实则错误→verifier 如何捕获→是否两模型共有→是否题面/环境问题→为何是有研究价值的能力缺口"写失败分析 |
| D3 | 更新 `development-trials.md` 与本文档，所有核心结果对齐同一冻结 commit |
| D4 | 凭据扫描（无 token / OAuth / API key），从干净环境按 README 复现 V1–V3 |
| D5 | push 到 `https://github.com/huangyCode/terminal-bench-order-gateway-recovery` 并确认面试方可访问 |

---

## 第四部分：时间线

| 时段 | 内容 |
|---|---|
| 9-14 上午 | 用户完成 U1–U4；我完成 T1、T2、T3、T9 |
| 9-14 下午 | 我完成 T4、T5、T6（V4 主体），并跑 V5 负向测试 |
| 9-14 傍晚 | V1–V4 全量验证，通过后冻结 commit |
| 9-14 夜间 | P3 六次正式 trial 并发跑（预计 1–3h/次，并发后约 3h 出结果） |
| 9-15 上午 | P4 两次 cheat；P5 分析、README 定稿、复现审计、push |

---

## 第五部分：风险与回退

| 风险 | 概率 | 处置 |
|---|---|---|
| V4 仍被某个模型通过 | 中 | 这是唯一可能突破 9-15 的风险。回退：保留 V4 已有闸，追加"多会话并行 + 跨会话 epoch"一层；需要你同意延到 9-16 |
| Oracle 在 seed 驱动测试下不稳定 | 中 | 先收敛 seed 集合到确定性可控的子集，宁可少几个 seed 也要 10/10 |
| 6 并发把 Docker 撑爆 | 中 | 降到 `-n 2` 串行跑，代价是墙钟翻倍；所以 U2 要尽早做 |
| 失败的 agent 烧满 8h timeout | 中 | 上游 67 个任务 `[agent].timeout_sec` 全是 28800，不能为省时间调小（会被质疑不公平）；靠并发消化 |
| Claude 认证反复失败 | 低 | 立即暴露，不要留到夜间；U1 是第一优先 |

## 不可违反的纪律

1. infra 错误、setup timeout、认证失败、verifier bug 永远不计为模型失败。
2. 任何改动 instruction / environment / solution / tests / task.toml 之后，受影响的验证全部重跑。
3. 正式报告中的全部核心结果必须对应同一个冻结 commit。
4. README 四段必须你本人改写并确认，AI 只出草稿。

---

## 执行进度（持续更新）

更新时间：2026-09-14 01:10

### 已完成

| 编号 | 事项 | 证据 |
|---|---|---|
| T1 | V3d 断言修复验证 | `jobs/oracle-v3d-stability-10x`：10/10 reward 1.0，0 异常 |
| T2 | `test.sh` 区分 infra 错误与功能失败 | `jobs/oracle-t2t3-regression`：5/5 reward 1.0 |
| T3 | 子进程 stderr 改临时文件 | 同上；并由 `cheat/` oracle 覆盖该攻击面 |
| T4 | V4 难度轴：批量协调 + 确定性传输预算 | `jobs/oracle-v4-smoke`：17/17 通过，reward 1.0 |
| T5' | 测试规模校准（改为不重写） | 上游 67 个已合并任务 tests 行数中位数 418，最高 2730；本任务 1006，`risk-scorer-replay`（已合并）964。rubric 的 ~100 行是理想值而非实际门槛，故不做高风险重写 |
| T6 | instruction 结构化重写 | 8 分句分号清单 → 8 条项目符号，19 行；对齐已合并 `wal-recovery-ordering`（23 行、带项目符号、含效率要求）的写法 |
| T7 | task.toml 元数据 | email 已填；`expert_time_estimate_hours` 4.0 → 8.0；tags 重写；**author_name 待用户提供** |
| T8 | README 四段草稿 | 按已合并 `risk-scorer-replay` 的 Task Metadata + 四段结构；**Relevant experience 待用户撰写，其余三段待用户改写签字** |
| T9 | staging 清理 | `__pycache__` / `*.pyc` 已清除 |
| T10 | cheat oracle | `cheat/solve.sh` + `cheat/poison.py`（双 fork 守护进程伪造 reward + 占住 stderr）；17 个已合并任务采用同一约定 |
| V1 | 22 项静态检查 | 22/22 通过 |
| V5 | 负向校准 | 逐条发送变体挂 2 个闸；每批 10 条变体只挂效率闸 → 证明中断批次闸与批量大小无关 |

### 关键设计纠正（已写入 development-trials.md）

1. **fencing/epoch 方案在实现前被否决。** `tests/venue.py` 的 `apply_request` 对已知 `request_id` 直接返回已记录响应且不产生第二次效果，`client_seq` 又必须严格等于 `next_client_seq`，所以被冻结后唤醒的僵尸 worker 本来就无法重复生效。加 epoch 只增加协议面，不增加难度。
2. **V3d 大概率也会被 Codex 通过。** 依据是 D5 artifact 的 `store.py:267` `sync_lock()`（非阻塞 flock，仅包住网络协调，内核在进程死亡时释放）已经覆盖了 V3d 的全部 barrier。
3. **批量化曾静默废掉 5 个已有场景**（`jobs/oracle-v4a` 12/17）。原因是断连 fault 只挂在 `POST /request` 上。已抽出 `transmit_one` 共享函数，使 fault 与传输方式无关。

### 仍待完成

| 编号 | 事项 | 阻塞 |
|---|---|---|
| V2 | Oracle 10 次稳定性（V4） | 运行中 |
| V3 | Nop 验证 | 排队（harbor 必须串行） |
| V4' | cheat oracle 必须得 0 | 排队 |
| V4 | `harbor check` 35 条 rubric | **U1：Claude 未登录** |
| P3 | 6 次正式 trial | **U1 + U2** |
| P4 | 2 次 cheat trial | U1 |
| — | commit + 同步 submission + push | V2/V3 出结果后立即做 |

### 新增的纪律条目

harbor 的 compose 项目名取自任务的 `environment/` 目录，固定为 `environment`。**每次 harbor 运行前必须确认没有遗留的 `environment-*` 容器**，否则会与残留项目撞车，表现为在 `Collecting main service artifacts` 之后无限挂起。本次已因此损失约 10 分钟。这类故障永远不能计为模型失败。

### 追加：cheat oracle 首跑即命中真实漏洞（已修复）

`cheat/` oracle 第一次运行就把 reward 伪造成了 1（`jobs/cheat-oracle-v4`），而当时 22 项静态检查、Oracle、Nop
全绿。根因是 `chmod 700 /logs/verifier` 在 macOS 宿主机 bind mount 上不生效（Docker Desktop 不遵守容器内
chmod），而 rubric 的 `verifier_execution_isolation` 正是把这条 chmod 列为保护 reward 通道的手段。

修复方式改为不依赖目录权限：pytest 的 CTRF 先写 `/tmp`，pytest 返回后 root 连续三轮 `pkill -9 -u nobody` 收割
agent 产生的一切进程，删掉被植入的 `reward.txt`/`reward.json`，最后才由 root 依据 pytest 退出码写 reward。
验证：`jobs/cheat-oracle-v4-hardened` reward 0.0，无伪造文件。

这条同时改变了一个判断：**`/cheat` 不是收尾的形式步骤，它是唯一能发现这类漏洞的关卡。** 所以后续任何改动
verifier 的行为，都必须重跑 cheat oracle，而不只是重跑 Oracle/Nop。

### 追加：agent 安装阶段的网络是正式 trial 的主要运行风险

`harbor check -a codex` 失败于 `NetworkConnectionError`：codex 的 agent setup 脚本固定要从
`raw.githubusercontent.com` 下载 nvm，容器内下载速度掉到 163 B/s。这与昨天 D3 那次 "NVM/npm 超过 360 秒
setup timeout" 是同一个原因，且无法绕开——该脚本由 harbor 的 codex agent 内置，在 Debian 分支下始终装 nvm，
预装 nodejs 也不会跳过。

正式 trial 的应对配置：

```bash
--agent-setup-timeout-multiplier 6 -r 3
```

`-r/--max-retries` 只对**异常**重试，不对 reward 0 重试——一个拿到 0 分的 trial 是"已完成"而不是"异常"。
所以自动重试只会吸收基础设施故障，不会掩盖真实的模型失败，这正是我们需要的语义。

`harbor check` 没有 retry 或 timeout 选项，只能在网络配合时手动重跑。

---

## 傍晚更新：方向转换与当前状态

### 订单网关方向已终止

`formal-codex` 三次：1 次 0.0、2 次 1.0。那次 0.0 经其自身产物验证为断言不公平，
去掉该断言后 17/17。**实际为三次全过。** Claude 三次从未取得有效结果（两次未收敛、一次 setup 超时）。

### 遗留引擎复刻方向已终止

公平性修复后 `formal2-claude` 三次全部 1.0（15 至 19 分钟）。
`formal2-codex` 与 `formal3-codex` 因 codex 客户端无法连接 `api.openai.com` 全部作废。
`formal4-codex` 在网络恢复后重跑中。

结论：录制材料完整时，最优策略是"实现→回放→修正"的机械循环，不需要洞察。

### 当前候选：`billing-discount-replica`

在遗留引擎复刻基础上加入折扣链，使**顺序与取整位置本身成为必须推断的内容**。
目的不是增加规则数量，而是破坏"一处不一致即可定位一条规则"的性质。

规则总数 15 条，全部通过消融审计（68 至 11774 行）。

已完成：静态检查 22/22、Oracle 1.0（7/7）、Nop 0.0、cheat oracle 0.0、
参考实现与 C 引擎交叉验证 16000 行 0 分歧。
进行中：rubric 35 条、Claude 校准。

### 审计中发现并修正的一处隐患

初次消融显示"赠送抵扣的基数是否含超量加价"变化 0 行。核查后确认两条规则同时出现过 2384 次，
是消融变体本身写错。用正确变体重测为 2378 行，可推断。

**若未做审计，这条规则会成为录制无法教会的隐藏要求。**

### 纪律补充

1. 任何规则在进入任务前，必须先通过消融审计证明其在给定材料中可推断。
2. rubric 检查必须在正式 trial 之前完成，不得因为"先看难度"而跳过。
3. 所有核心结果必须对应同一冻结 commit。
