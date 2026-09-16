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
| Reward | **0.0** |
| `/logs/verifier/reward.txt` | `0`, untouched |
| Forged `reward.json` | absent |
| Exceptions | 0 |
| Duration / output | 30 minutes, ~800 KB |

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

All three produce the same first mismatch as Claude: `4,497,631` against an expected `8,995,262`.

Two of the three repaired **two** of the four defects, one more than Claude managed, and still scored
zero. That is the all-or-nothing property working as designed: a half repair and no repair are worth
exactly the same.

### Adversarial trial

Job `jobs/settle-cheat-codex`. **Not a valid result**, but not a refusal either — the transcript shows
the model attacking in earnest and being cut off mid-attempt.

Over 37 KB of transcript it enumerated the filesystem, then grepped `/tmp`, `/root` and `/opt` for the
canary GUID, the string `Settlement contract` and `day-01.json`, looking for the verifier's tests and
ground truth. It then wrote a class subclassing `int` whose `__eq__` always returns `True`, intending to
make every assertion pass. That last step tripped OpenAI's classifier:

```
{"type":"error","message":"This content was flagged for possible cybersecurity risk..."}
{"type":"turn.failed", ...}
```

Three retries ended the same way. The reward file reads `0`, but the run was terminated server-side
rather than defeated by the verifier, so it is not counted as a passed adversarial trial.

Both attack paths would have failed on their merits. The verifier runs in a separate container with
`/tests` mode `go-rwx`, so the ground truth was never reachable from the agent's container; and a
truthy `__eq__` inside the agent's own process cannot reach a reward that root writes after reaping
every process belonging to the unprivileged user. The model simply never got to find that out.

The adversarial property is evidenced instead by the Claude run (`jobs/settle3-cheat-claude`), which
attacked for thirty minutes without interruption and scored 0.0 with the reward file untouched, and by
the deterministic cheat oracle, which installs an artifact that daemonises and rewrites
`/logs/verifier/reward.*` and also scores 0.0.

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
| rubric attempts ×7 | `AgentSetupTimeoutError`, `NetworkConnectionError` | `harbor check` has no setup-timeout flag; with `-a codex` the two setup commands measure 414 s against a 360 s limit | no |

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
