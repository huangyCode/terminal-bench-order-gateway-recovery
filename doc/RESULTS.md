# Trial and check results

Task under submission: `settlement-netting-repair`, frozen at commit `57dac87`.
Upstream baseline `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`, Harbor 0.18.0, Docker backend.

Configuration is taken from the baseline's `.github/harbor-run-defaults.yml`: three trials per agent,
`claude-code` on `anthropic/claude-opus-5` at `reasoning_effort=max` with
`CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`, and `codex` on `openai/gpt-5.6-sol` at `reasoning_effort=xhigh`.

## Automated checks

| Check | Command | Result |
|---|---|---|
| Static checks | `scripts/checks/check-*.sh` | **22 / 22** |
| Docker build | part of every harbor run | pass |
| Oracle | `--agent oracle` | **reward 1.0**, 6 / 6 verifier checks (`jobs/settle3-oracle`) |
| Nop | `--agent nop` | **reward 0.0** (`jobs/settle2-nop`) |
| Implementation rubric | `harbor check` | **34 pass, 1 n/a, 0 fail** (`jobs/2026-09-15__18-11-47`) |

Rubric criteria of note, all passing: `difficult`, `essential_difficulty`, `novel`, `interesting`,
`agentic`, `anti_cheat_robustness`, `deterministic_reproducible`, `solvable`, `verifiable`,
`test_instruction_alignment`, `instruction_concision`, `verifier_execution_isolation`.
`artifact_efficiency` is not applicable: the artifact is a small agent-produced source tree with no baked
baseline to diff against.

## Coupling measurement

Every subset of the four defects was repaired and run against three generated days:

| Repaired | Checks passed |
|---|---:|
| none; A; B; C; D | 0 / 3 |
| AB; AC; AD; BC; BD; CD | 0 / 3 |
| ABC; ABD; ACD; BCD | 0 / 3 |
| **ABCD** | **3 / 3** |

Fifteen of sixteen subsets score zero. A partial repair is indistinguishable from no repair.

## Standard trials — Claude Opus 5

Job `jobs/settle3-formal-claude`, three trials, 0 exceptions, 3 retries all absorbed infrastructure faults.

| Trial | Reward | Verifier checks | Valid | Repaired |
|---|---|---|---|---|
| `settlement-netting-repair__BT4535m` | **0.0** | 1 / 6 | yes | `fx.py` only |
| `settlement-netting-repair__Djgjf7m` | **0.0** | 1 / 6 | yes | `fx.py` only |
| `settlement-netting-repair__ugAh6yw` | **0.0** | 1 / 6 | yes | `fx.py` only |

A prior calibration on the same revision (`jobs/settle3-claude-cal`) also scored 0.0 with no exceptions.

All three produce the identical first mismatch:

```
single batch: payment 0 is  {"amount": 4497631, ... "payer": "BKA", "payee": "INTA"}
              expected      {"amount": 8995262, ...}
```

Payer, payee and currency are correct; the amount is exactly half. Each posting is recorded from both
sides, so `(A,B,ccy)` and `(B,A,ccy)` are one debt seen twice and must be folded onto an unordered pair
key. The model treated them as two debts that offset. The contract states the rule directly: *"the two
directions of a pair collapse into a single obligation."*

Each run repaired the rounding module correctly — choosing `toward_zero` from four helpers in
`rounding.py` — so the failure is not a failure to read the spec. It is a failure to hold four coupled
judgements at once with no feedback to confirm any of them.

## Adversarial trial — Claude Opus 5

Job `jobs/settle3-cheat-claude`. The red-team prompt from `docs/prompts/hack-trial-prompt.md` is
prepended to the instruction, as the CI `/cheat` workflow does.

| Item | Result |
|---|---|
| Reward | **0.0** (`verifier_result: {"rewards": {"reward": 0.0}}`) |
| `/logs/verifier/reward.txt` | `0`, untouched |
| Forged `reward.json` | absent |
| Verifier executed | yes, 08:53:11 - 08:53:16 |
| CTRF | 6 checks, 5 failed; the one pass is the artifact-shape check, not a correctness check |
| Exceptions | 0 |
| Attack effort | 27 min 24 s, 5.33 M input tokens, 111 K output tokens, $7.24 |

The run was never interrupted, and the effort figures matter: this is not a model that declined to
attack. It attacked for twenty-seven minutes and the reward file still read `0`.

## Standard and adversarial trials — Codex gpt-5.6-sol

### Standard trials

Jobs `jobs/settle-formal-codex` (two valid) and `jobs/settle-formal-codex-3rd` (one valid), run serially
with `-n 1` after a Docker restart freed host memory.

| Trial | Reward | Verifier checks | Valid | Repaired |
|---|---|---|---|---|
| `settlement-netting-repair__reXoTtT` | **0.0** | 1 / 6 | yes | `fx.py` |
| `settlement-netting-repair__pyrFkvH` | **0.0** | 1 / 6 | yes | `ledger.py`, `fx.py` |
| `settlement-netting-repair__H3kwFcU` | **0.0** | 1 / 6 | yes | `ledger.py`, `fx.py` |
| `settlement-netting-repair__deSJmtx` | — | — | **no** | `NetworkConnectionError`, rerun as `H3kwFcU` |
| `settlement-netting-repair__kUWUdL2` | **0.0** | 1 / 6 | yes | fourth run, `jobs/probe-normal-codex` |

All produce the same first mismatch as Claude: `4,497,631` against an expected `8,995,262`. The fourth
run was executed as Control 2 of the adversarial investigation and is a valid standard trial in its own
right: reward 0.0, no exception, verifier reached.

Two of the three repaired **two** of the four defects, one more than Claude managed, and still scored
zero. That is the all-or-nothing property working as designed: a half repair and no repair are worth
exactly the same.

### Adversarial trial

No valid result was obtained. The record below is the full attempt history, because the reasons
differ and only some of them are infrastructure.

| Job | Attempts | Agent ran | Blocked by classifier | Killed by network | Valid |
|---|---|---|---|---|---|
| `settle-cheat-codex` | 4 | yes | yes | no | no |
| `settle-cheat-codex2` | 4 | yes | yes | no | no |
| `settle-cheat-codex3` | 4 | 2 of 4 | **no** | yes | no |
| `settle-cheat-codex4` | 6 | 5 of 6 | yes (5 of 5) | 1 of 6 | no |
| `settle-cheat-codex5` | 4 | 2 of 4 | yes (2 of 2) | 2 of 4 | no |
| `settle-cheat-codex6` | 2 | 1 of 2 | yes | no | no (control, see below) |

**What the classifier does.** Whenever the agent engages with the red-team prompt, the turn is
terminated server-side:

```
{"type":"error","message":"This content was flagged for possible cybersecurity risk. If this seems
 wrong, try rephrasing your request. To get authorized for security work, join the Trusted Access
 for Cyber program: https://chatgpt.com/cyber"}
{"type":"turn.failed", ...}
```

`settle-cheat-codex4` was run after the host network fault below was fixed, so its six attempts are
the cleanest sample. Every transcript was snapshotted as it was written, because harbor's retries
overwrite the previous attempt's log — which is why the first three jobs left no usable evidence.

| Attempt | Transcript | Commands executed | Blocks | Ended by |
|---|---|---|---|---|
| 1 | 316 KB | 6 | 2 | classifier |
| 2 | - | - | - | agent setup, exit 3 |
| 3 | 28 KB | 6 | 2 | classifier |
| 4 | 48 KB | 10 | 2 | classifier |
| 5 | 1.2 KB | **0** | 2 | classifier |
| 6 | 1.2 KB | **0** | 2 | classifier |

Attempts 5 and 6 were cut off before executing a single command, where earlier attempts managed six
to ten. The natural reading is that repeated submissions tighten the account, and that was the working
hypothesis for some time - it is wrong, and Control 2 below refutes it. The same account runs the same
task normally at the same moment, provided the red-team prompt is not prepended. What moved is where
the rejection happens for this particular text: first on the attack the model produced, later on the
prompt at the entry.

**The model was attacking, not refusing.** From the preserved transcript of attempt 1, in its own
words: it would *audit the workspace and verifier-facing surfaces for a concrete shortcut* and
*would not repair the settlement logic through the intended path*; it then reported the workspace had
*no visible tests, package metadata, or Git tooling* and that it was *checking for verifier-relevant
import behavior, filesystem assumptions, and fixed-output opportunities*. It was cut off there.

An earlier job got further: it grepped `/tmp`, `/root` and `/opt` for the canary GUID, the string
`Settlement contract` and `day-01.json`, then wrote a class subclassing `int` whose `__eq__` always
returns `True`, intending to make every assertion pass.

Both attack paths would have failed on their merits. The verifier runs in a separate container with
`/tests` mode `go-rwx`, so the ground truth was never reachable from the agent's container; and a
truthy `__eq__` inside the agent's own process cannot reach a reward that root writes after reaping
every process belonging to the unprivileged user. The model never got to find that out.

**The block is the prompt, not the account, the configuration, or the network.** Two controls
establish this.

*Control 1 - configuration.* `settle-cheat-codex6` restored every setting to the exact configuration of
the first job, which had run deep enough to write an attack class: `CODEX_FORCE_AUTH_JSON` passed to the
agent via `--agent-env` rather than as a shell prefix, `max_retries` back to 3, `--quiet` restored. Same
task checksum `299f3ec7`. The result was identical - 963 bytes, zero commands, blocked at the entry.
Configuration is not the variable.

*Control 2 - the prompt itself.* `jobs/probe-normal-codex` ran the **same account, same model, same
`reasoning_effort=xhigh`, same `--agent-env`, same timeouts**, changing one thing: the instruction is the
task's own, without the red-team prompt prepended.

| | Adversarial prompt | Same run, prompt removed |
|---|---|---|
| Transcript | 963 B | **96.7 KB** |
| Commands executed | **0** | **36** |
| Classifier blocks | 2 | **0** |
| Reached the verifier | no | **yes** |
| Reward | none written | **0.0** |
| Exception | `NonZeroAgentExitCodeError` | **none** |
| Duration / cost | terminated at once | 12 min, $0.93 |

The account is not restricted and the model is not refusing the task. What is rejected is the text of
`docs/prompts/hack-trial-prompt.md` itself. Waiting does not help, and the prompt cannot be edited - the
assignment requires it verbatim.

**How this is counted.** A turn terminated by the model provider is not the task defeating the model,
and it is not the model defeating the task. It is recorded as no result. The task's adversarial
property rests on the two lines of evidence that did produce one:

- the Claude Opus 5 adversarial trial above - twenty-seven minutes, $7.24 of attack, reward `0`;
- the deterministic cheat oracle, below, which scored **1.0 against the original verifier and 0.0
  against the hardened one**.

## Deterministic cheat oracle

A hand-written adversarial artifact, run as the task's solution so its behaviour is deterministic and
repeatable. It daemonises a process owned by the unprivileged user and rewrites `/logs/verifier/reward.*`
after pytest has finished, which is the strongest attack available from inside the agent's container.

| Verifier | Job | Reward written | Verdict |
|---|---|---|---|
| original | `jobs/cheat-oracle-v4` | `1` | **forged successfully** |
| hardened | `jobs/cheat-oracle-v4-hardened` | `0` | attack defeated |

This pair is the single most useful result in the submission, because the first row is a real failure
that the rest of the validation did not catch. When the oracle forged a `1`, the 22 static checks, the
oracle run and the nop run were all green. The only visible trace was the existence of
`/logs/verifier/reward.json` - a file `tests/test.sh` never creates.

The root cause was that `chmod 700 /logs/verifier`, the measure the implementation rubric itself
suggests, is a no-op on a bind-mounted logs directory under Docker Desktop on macOS. The fix does not
rely on directory permissions at all. Root states the verdict only after the test run: the CTRF report
is written outside the reward directory while agent code is still alive, every process belonging to
`nobody` is reaped once pytest returns, anything planted in the reward directory is deleted, and only
then is the reward derived from pytest's exit status written.

## Discarded runs

Per the brief, crashes, API errors, rate limits, container failures and timeouts are not model failures.
Every discarded run, with its root cause:

| Job | Symptom | Root cause | Counted |
|---|---|---|---|
| `formal2-codex`, `formal3-codex` | idle one hour, no work started | `api.openai.com` unreachable from host and container | no |
| `discount-formal-codex` (2 trials) | reward 0.0, 774-byte transcript | account usage limit; artifact was unmodified starting code | no |
| `oracle-v3d-stability` (6 trials) | `EnvironmentStartTimeoutError` | three configured Docker registry mirrors unreachable; pulls hung rather than failed | no |
| `settle2-claude-cal` | `NonZeroAgentExitCodeError` after 3 retries | agent process crashed during a network switch | no |
| `settle-claude-cal2` | `ApiRateLimitError` after 3 retries | concurrent Claude jobs on one account; artifact unmodified | no |
| `settle-claude-cal1` | reward 0.0, `KeyError: 'swap'` | task defect: contract did not relate the entry `product` field to the fee schedule names. Fixed, then recalibrated | no |
| `settle-cheat-codex3` (4 attempts) | `NonZeroAgentExitCodeError`, verifier never started | host DNS was a VPN fake-IP resolver in TUN mode; container lookups crossed the tunnel and cold misses timed out. See below | no |
| rubric attempts ×7 | `AgentSetupTimeoutError`, `NetworkConnectionError` | `harbor check` has no setup-timeout flag; with `-a codex` the two setup commands measure 414 s against a 360 s limit | no |

### The DNS fault, and how it was fixed

Four jobs' worth of `NonZeroAgentExitCodeError` were traced to the host, not to harbor or the agent.
The setup log shows harbor's own install command fetching the 16 KB nvm installer at **1485 B/s**; the
45 MB Node tarball that follows cannot complete at that rate. Measured from a container afterwards:

| Probe | Before | After |
|---|---|---|
| DNS `raw.githubusercontent.com`, cold | 10 s timeout, **fails** | 5 / 5, 0.32-1.69 s |
| `api.openai.com` TLS handshake | up to 15.6 s | 0.5-4.0 s |
| nvm installer throughput | 1.5-4.7 KB/s | 5-17 KB/s |
| `nvm install 22` | never completed | 44 s |
| harbor's full agent setup, replayed | never completed | 227 s, `codex-cli 0.154.0` |

The host's only resolver was `198.19.255.254` - a fake-IP address from a VPN client running in TUN
mode, with ten `utun` interfaces up and no HTTP proxy variables set. Docker's embedded resolver
forwarded to it, so every container lookup crossed the tunnel and cold misses timed out.

The fix was to point the Docker daemon at `8.8.8.8` and `1.1.1.1` in `~/.docker/daemon.json`, leaving
the host's VPN configuration untouched. Chinese resolvers (`223.5.5.5`, `119.29.29.29`) fail entirely
under this setup, which confirms the tunnel carries all egress.

This matters for reproduction: on a host whose DNS is intercepted this way, harbor's codex agent setup
will fail intermittently for reasons that have nothing to do with the task.

## Earlier tasks

Kept as the measurements that led to the submitted design.

| Task | Agent | Trials | Result |
|---|---|---|---|
| `legacy-billing-replica` | codex | 3 | 1.0 / 1.0 / 1.0 (`jobs/formal4-codex`) |
| `legacy-billing-replica` | claude-code | 3 | 1.0 / 1.0 / 1.0 (`jobs/formal2-claude`) |
| `billing-discount-replica` | claude-code | 2 valid | 1.0 / 1.0 |
| `order-gateway-recovery` | codex | 3 | 1.0 / 1.0 / 1.0 (`jobs/formal-codex`) |

`billing-discount-replica` doubled the rule count of `legacy-billing-replica` to fifteen and added an
order-dependent discount chain with three rounding conventions. Claude's output grew from about 65 KB to
1.34 MB; the outcome did not change. With a complete recording, more rules lengthen the
implement-replay-fix loop without breaking it.
