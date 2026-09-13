# Terminal-Bench 3 面试任务：阶段状态与执行归档

归档时间：2026-09-13（Asia/Shanghai）  
项目：`terminal-bench-3-interview-task`  
任务：`order-gateway-recovery`  
GitHub：<https://github.com/huangyCode/terminal-bench-order-gateway-recovery>  
本归档的目的：冻结当前事实，区分“已完成、已验证、开发失败、基础设施失败、尚待验证”，避免后续迭代混淆结果。

## 1. 面试题要求与我们对目标的理解

这不是让候选人创建一个新 agent，也不是重新实现整套 benchmark 框架。交付物是一道原创 Terminal-Bench 3 task：给 agent 一个有缺陷的终端工程环境、公开任务说明和可操作接口；agent 在容器中修复工程；独立 verifier 判断最终状态是否真正满足要求。

最终交付必须同时满足：

1. 跟随当前 TB3 contribution、CI、review 文档，而非只依赖招聘邮件摘要。
2. 通过全部 static checks、implementation-rubric checks、Docker build、Oracle、Nop。
3. 标准 `/run`：当前 CI 指定的 Codex `openai/gpt-5.6-sol`、`xhigh` 和 Claude Code `anthropic/claude-opus-5`、`max`，每种配置 3 次，6 次都必须是有效 verifier 失败。
4. crash、API/rate-limit、登录、容器、超时等异常不算模型失败。
5. `/cheat`：Codex 与 Claude 各 1 次，reward 必须都是 0；任何非零 reward 都说明 verifier 可被绕过。
6. 仓库记录所有命令、配置、结果和简要失败分析。

面试官真正观察的不只是题目是否“难”，还包括：独立研究当前规则、系统设计品味、verifier 是否可信、是否诚实分类失败、能否用 agent trials 校准难度、迭代过程是否可复现，以及是否能说明为什么模型失败。

## 2. 当前工程与仓库位置

- 项目根目录：`/Users/grailor/Documents/Work/terminal-bench-3-interview-task`
- 官方 TB3 开发克隆：`/Users/grailor/Documents/Work/terminal-bench-3-interview-task/repository`
- 干净提交仓库：`/Users/grailor/Documents/Work/terminal-bench-3-interview-task/submission`
- 项目文档：`/Users/grailor/Documents/Work/terminal-bench-3-interview-task/doc`
- 当前 task：`repository/tasks/order-gateway-recovery`
- Harbor jobs：`repository/jobs`
- 官方上游冻结基线：`e2995b93b0a46edee7bc9942ea5622411a6d5bb9`
- 开发分支：`task/crash-safe-order-gateway`
- 当前 GitHub 最新稳定提交：`d92266b Add concurrent gateway recovery`（V3c）
- 当前本地开发 HEAD：`fb9b33e Add concurrent gateway recovery`，其上有尚未提交的 V3d 修改。

安全说明：对话中曾出现 GitHub PAT。该 token 不被写入仓库或本文档，也没有被继续使用；应在 GitHub 中撤销。push 使用本机现有安全 `gh` 登录。

## 3. 当前 task 的系统设计

题目模拟一个 crash-safe order gateway：

- gateway 使用 SQLite 持久化；
- venue 是独立持久进程，通过 HTTP session protocol 通信；
- gateway 对外提供 JSON-lines 命令接口；
- 支持 NEW、REPLACE、CANCEL 的 durable request chain；
- client sequence 与 venue delivery sequence 相互独立；
- 网络可能在 venue commit 前或 commit 后断开；
- gateway 必须保留原 business identity，正确设置 `poss_dup`；
- venue 可请求 resend range，gateway 必须选择 GAP_FILL 或完整 REPLAY；
- future inbound event 必须跨 restart 缓冲；
-相同 `exec_id` 可在新的 venue sequence 再投递：delivery cursor 要推进，但 business effect 只能发生一次；
- 多个 gateway process 可共享一个 SQLite database，并发 submit/sync；
- 一名 worker 被杀后，其他 worker 必须接管并收敛。

Verifier 位于 separate verifier container。权威 venue 由 verifier 自己启动，agent 无法读取 verifier 代码、控制 fault injection 或直接访问 venue 数据库。最终 reward 只从 verifier 结果生成。

## 4. 版本与修改思路

### V1：纵向原型

目标：验证 task 包结构、独立 verifier、gateway crash/restart、Oracle/Nop 基本链路。

结果：Codex 修复功能，但早期 verifier 错误禁止 `.pyc`，导致 reward 0。该结果是 verifier 设计错误，不是有效模型失败。随后移除不合理限制。

结论：原型太浅，仅证明 harness 可执行。

### V2a：独立 venue 与 ambiguous commit

加入独立 HTTP venue。venue 可在 durable commit 后关闭连接、不返回 HTTP response；gateway 必须从 session history 发现已经提交的结果，不能创建第二次业务效果。

- Static：22/22 通过
- Oracle：`jobs/2026-09-13__01-35-20`，1.0
- Nop：`jobs/2026-09-13__01-35-48`，0.0

### V2b：NEW/REPLACE/CANCEL durable chain

加入稳定 request ID、`previous_request_id`、desired/current request、跨 restart 未完成 request chain。

- Oracle：`jobs/2026-09-13__01-41-08`，1.0
- Nop：`jobs/2026-09-13__01-41-38`，0.0
- 两个更早 Oracle 暴露测试环境假设，后将权威 venue 移入 verifier boundary。

### V2c：双 ambiguous commit 与 process hygiene

NEW 和 REPLACE 分别在 commit 后丢响应，gateway 每次都被 kill/restart。所有 gateway subprocess 使用独立 process group，测试结束 kill 整组，防止遗留进程污染后续 case。

- Oracle stability：`jobs/2026-09-13__09-51-09`，3/3 通过
- Nop：`jobs/2026-09-13__09-52-21`，0.0
- implementation-rubric：`jobs/2026-09-13__09-49-40` 因 Claude `authentication_failed / Not logged in`，是无效基础设施输出。

### D2：Codex V2c 难度校准

- 配置：Codex / `openai/gpt-5.6-sol` / `reasoning_effort=xhigh`
- Job：`jobs/codex-v2c-calibration`
- 运行：20m26s
- Reward：1.0
- Exceptions：0

结论：有效通过，V2c 太容易；不能计为招聘要求的失败。

### V3a：outbound resend、GAP_FILL 与 REPLAY

加入 venue-requested resend range。已知接受的序列必须 GAP_FILL；venue 已接受但 gateway 缺失 response 的序列必须携带原 identity、原 sequence 和 `poss_dup=true` 做 REPLAY。另加入 commit 前断连，要求在第一次 I/O 前持久化 `send_attempted`。

- Oracle：`jobs/2026-09-13__10-19-16`，1.0
- Nop：`jobs/2026-09-13__10-20-14`，0.0

### D3：Codex V3a 难度校准

- 首次 `jobs/codex-v3a-calibration`：NVM/npm 超过 360 秒 setup timeout，属于无效基础设施失败。
- 有效重试：`jobs/codex-v3a-calibration-retry`
- 运行：27m49s
- Reward：1.0
- Exceptions：0

结论：仍然太容易。

### V3b：inbound gap、restart buffer 与重复业务事件

venue request ledger 与 event delivery log 分离。Verifier 隐藏 venue sequence 2 但提供 sequence 3；sequence 3 重复 sequence 1 的稳定 `exec_id`。gateway 必须持久化未来事件，restart 后补齐 sequence 2，delivery cursor 到 4，同时重复业务事件不重复生效。

- Oracle：`jobs/2026-09-13__14-52-20`，1.0
- Nop：`jobs/2026-09-13__14-53-10`，0.0
- 更早 Oracle `14-50-50` 暴露参考解使用旧 session snapshot，已修为 outbound progress 后最终 refresh。

### D4：Codex V3b 难度校准

- Job：`jobs/codex-v3b-calibration`
- 运行：约 41m37s
- Reward：1.0
- Exceptions：0
- Verifier：13/13

结论：耗时增加，但仍是有效通过。

### V3c：双 gateway process 共享 SQLite

两个 process 并发提交 8+8 个订单；要求 16 个唯一、无缺口 client sequence；同时 sync 同一 venue；kill 一名 worker 后 survivor 收敛；本地 16 个 NEW 与 venue ledger 对齐。

实现侧补强：

- SQLite `timeout=30`、`busy_timeout=30000`、WAL；
- busy/locked bootstrap 有界重试；
- mutation 使用 `BEGIN IMMEDIATE`；
- Oracle 的关键 mutation 全部使用 immediate transaction。

验证：

- 初次 Oracle：`jobs/2026-09-13__15-41-30`，1.0
- 首次 5-run：`jobs/2026-09-13__15-42-44`，仅 2/5，发现 bootstrap race
- 修复后：`jobs/2026-09-13__15-46-12`，5/5，全部 1.0，0 异常
- Nop：`jobs/2026-09-13__15-52-58`，0.0
- Static：22/22
- GitHub commit：`d92266b`

### D5：Codex V3c 难度校准

- Job：`jobs/codex-v3c-calibration`
- 配置：Codex / `openai/gpt-5.6-sol` / `xhigh`
- 运行：43m03s
- Reward：1.0
- Exceptions：0
- 输入 token：1,840,239（其中 cache 1,757,312）
- 输出 token：54,450

Codex 的成功策略：

1. 用 `BEGIN IMMEDIATE` 保护序列分配和意图更新；
2. 用 `fcntl.flock` 将网络 reconciliation 降为单协调者；
3. kernel 在进程死亡后自动释放 flock；
4. 并发 sync 未拿锁时返回 retryable outcome；
5. 用 `acceptance_known` 区分 GAP_FILL 与 REPLAY；
6. 自行补了协议、断连、restart、resend 和真实 HTTP concurrency 测试。

结论：V3c 仍不能进入正式 3× trials。它增加了工作量，但全局 sync lock 把核心并发问题重新序列化。

### V3d：精确 coordinator handoff（当前开发中，未提交）

修改思路：不能只“某个 worker 最后被杀”，而要在最危险窗口精确杀死网络协调者。

新增 deterministic verifier barrier：

1. worker A 发送 sequence 1；
2. verifier-owned venue durable commit；
3. venue 在发送 HTTP response 前阻塞；
4. verifier 确认 commit 已发生；
5. worker B 在 A 等待网络时，必须仍能持久化 REPLACE 与另一个 NEW；
6. SIGKILL worker A；
7. release venue handler；
8. venue 请求从 sequence 1 recovery，并隐藏 HANDOFF response；
9. worker B 必须 REPLAY 模糊 sequence 1，再按顺序发送新 suffix；
10. 检查 recovery log、session response order、本地 state 和 venue ledger，确保无丢失、无跳号、无重复业务效果。

公开文档已增加边界：其他 worker 必须在 network owner 等待 I/O 时仍可接受 durable intent；owner 在 venue commit 后、response 前死亡时，survivor 必须先恢复 ambiguous prefix 再发送新 suffix。

## 5. V3d 当前执行结果与未解决状态

### 首次验证

- Oracle：`jobs/oracle-v3d-handoff`，1.0，0 异常，41 秒
- Nop：`jobs/nop-v3d-handoff`，0.0，0 异常，约 1m01s

### 第一次 5-run 稳定性

Job：`jobs/oracle-v3d-stability`

- 3 次 Oracle 1.0
- 1 次 verifier 0.0
- 1 次 RuntimeError

分类：

- RuntimeError 是 Docker 拉取 `python:3.13-slim-bookworm` metadata 时镜像代理 TLS handshake timeout；属于基础设施失败，不是 task 或 model failure。
- Verifier 0.0 是旧 bootstrap race：一个并发 gateway 在 schema/WAL 初始化期间退出。

修复：将初始 busy/locked 重试由 40 × 0.05s（约 2 秒）提高到 200 × 0.05s（约 10 秒）；process 意外退出时 verifier 会输出 stderr。

### 第二次 5-run 稳定性

Job：`jobs/oracle-v3d-stability-fixed`

- 5/5 reward 0.0
- 0 exceptions

这不是 Oracle 功能失败，而是 verifier 自己的异常断言回归：`GatewayProcess.command` 攅读 stderr 后使用 `pytest.fail`；handoff test 仍只接受 `AssertionError/BrokenPipeError/OSError`，所以 owner 被预期 SIGKILL 后，future 抛出的 pytest failure 未被接住，五次都确定性失败。

已修改但尚未重新验证：future 抛出任意异常视为“被 kill 的 owner 没有返回 response”；如果 future 正常返回，测试才明确失败。语法检查生成的 `__pycache__` 已从 task staging 清除。

因此当前最准确状态是：**V3d 修复已写入本地，但修复后的 Oracle stability、Nop、Static、commit/push 和 Codex calibration 都尚未执行。**

## 6. 已执行的主要命令配置

Codex 标准配置：

```bash
harbor run -p tasks/order-gateway-recovery \
  --agent codex --model openai/gpt-5.6-sol \
  --env docker --yes \
  --ae CODEX_FORCE_AUTH_JSON=1 \
  --ak reasoning_effort=xhigh \
  --agent-setup-timeout-multiplier 3 \
  --job-name <job-name>
```

Oracle：

```bash
harbor run -p tasks/order-gateway-recovery \
  --agent oracle --env docker --yes \
  --job-name <job-name>
```

Oracle 5 次顺序稳定性：

```bash
harbor run -p tasks/order-gateway-recovery \
  --agent oracle --env docker --yes \
  -k 5 -n 1 \
  --job-name <job-name>
```

Nop：

```bash
harbor run -p tasks/order-gateway-recovery \
  --agent nop --env docker --yes \
  --job-name <job-name>
```

Claude 目标配置（尚未能有效执行）：

```bash
harbor run -p tasks/order-gateway-recovery \
  --agent claude-code --model anthropic/claude-opus-5 \
  --env docker --yes \
  --ae CLAUDE_FORCE_OAUTH=1 \
  --ae CLAUDE_CODE_OAUTH_TOKEN=<token> \
  --ak reasoning_effort=max
```

## 7. 尚未完成与阻塞项

### 工程待办

1. 重新运行 V3d 修复后的 5× Oracle stability，要求所有有效轮次 1.0、0 verifier failure。
2. 重跑 V3d Nop，必须 0.0。
3. 运行当前 CI 的 22 个 static checks。
4. 运行 Docker build 与 implementation-rubric。
5. commit/push V3d，仅在上述检查稳定后进行。
6. 运行一次 Codex V3d 开发校准。若仍 1.0，继续设计下一个真实系统边界；不能直接进入正式 trials。
7. 只有候选版本在开发校准中显示强模型失败趋势后，才冻结并运行正式 Codex 3 次、Claude 3 次。
8. 冻结 verifier 后运行 Codex `/cheat` 1 次、Claude `/cheat` 1 次，全部必须 0。

### 用户输入/环境待办

1. Claude Code 当前未登录。需要用户在本机执行 `claude setup-token`，否则 Claude trial 只能得到无效登录失败。
2. README 的 difficulty、solution、verification、relevant experience 依照上游 guide 必须是人类作者内容；AI 可整理草稿，但提交前用户需阅读、修改并确认。
3. `task.toml` author name/email 仍需用户提供。
4. clean submission 的最终 Git author identity 需要用户提供希望展示的姓名与 email。
5. 先前暴露的 GitHub PAT 应撤销。

## 8. 下一步恢复点

恢复工作时从以下顺序开始：

1. 确认 staging 和开发克隆中 V3d 的异常断言修复一致。
2. 运行 `oracle-v3d-stability-fixed2`，5 次顺序执行。
3. 若 5/5 通过，运行 Nop 与 22 static checks。
4. 更新本归档和 development trial log。
5. commit 到开发分支，同步 clean submission，push GitHub。
6. 运行 `codex-v3d-calibration`。
7. 根据 reward 做明确分支：reward 0 且无异常 → 再做重复校准；reward 1 → 复盘成功策略并继续提高真实状态机难度。

任何时候都不能把 infra error、agent setup timeout、auth failure 或 verifier bug 计成模型失败。

## 9. 当前结论

项目已经形成一套可信、原创、可执行的 TB3 task，并完成 V1→V3c 的多轮验证与难度校准；GitHub 上的 V3c 是稳定版本。但是最强 Codex 在 V2c、V3a、V3b、V3c 都有效通过，因此尚未达到招聘要求的标准失败率。

V3d 的方向是合理的：从“最终 kill 一个 worker”升级为“在 venue commit/HTTP response 的精确歧义窗口 kill 当前协调者，并要求另一 worker 同时接受新意图和接管旧 session”。当前唯一未闭环事项是刚修复的 verifier 断言尚未重跑。正式 trials 和 adversarial trials 仍未开始，Claude 登录仍是外部阻塞。
