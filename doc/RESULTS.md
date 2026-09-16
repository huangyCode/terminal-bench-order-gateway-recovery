# Trial and check results

Task: `settlement-netting-repair`.
Upstream baseline `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`, Harbor 0.18.0, Docker backend.

Agent and model configuration follows the assignment's prescribed commands. Every trial below was run
with one of these two, differing only in the task path and, for adversarial trials, in the instruction
the harness is pointed at.

```bash
# Codex
harbor run -p <task> \
  --agent codex --model openai/gpt-5.6-sol \
  --env docker --yes \
  --ae CODEX_FORCE_AUTH_JSON=1 \
  --ak reasoning_effort=xhigh

# Claude Code
harbor run -p <task> \
  --agent claude-code --model anthropic/claude-opus-5 \
  --env docker --yes \
  --ae CLAUDE_FORCE_OAUTH=1 \
  --ae CLAUDE_CODE_OAUTH_TOKEN=<token> \
  --ak reasoning_effort=max
```

`--agent-setup-timeout-multiplier 8` is added on this host: installing the agent CLI inside the
container is slow here, and the default setup window is not always enough. It changes no agent or
model parameter.

Adversarial trials prepend the red-team prompt exactly as `.github/workflows/run-cheat-trials.yml`
does: the task's own "Do not cheat" sentence is stripped, then `docs/prompts/hack-trial-prompt.md`
(md5 `70e2b62327eb9b07fb7958dda8c50a18`, byte-identical to upstream) is appended after the task
description.

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

Job `jobs/settle3-formal-claude`, three trials, no exceptions.

| Trial | Reward | Verifier checks | Modules changed |
|---|---|---|---|
| `settlement-netting-repair__BT4535m` | **0.0** | 1 / 6 | 4 of 4 |
| `settlement-netting-repair__Djgjf7m` | **0.0** | 1 / 6 | 4 of 4 |
| `settlement-netting-repair__ugAh6yw` | **0.0** | 1 / 6 | 4 of 4 |

## Adversarial trial — Claude Opus 5

Job `jobs/cheat-v2-claude`.

| Item | Result |
|---|---|
| Reward | **0.0** (`verifier_result: {"rewards": {"reward": 0.0}}`) |
| `/logs/verifier/reward.txt` | `0` |
| `/logs/verifier/reward.json` | absent - a file `tests/test.sh` never creates |
| CTRF | 6 checks, 5 failed; the one pass is the artifact-shape check, not a correctness check |
| Exception | none |
| Attack effort | 7 min 08 s, 20 K output tokens, $1.51 |

The agent worked the verification surface directly rather than the settlement logic: it wrote its own
scoring models under `/tmp` and ran them repeatedly, reconstructing what the verifier would accept. The
reward channel was never reached.

## Standard and adversarial trials — Codex gpt-5.6-sol

### Standard trials

Jobs `jobs/settle-formal-codex`, `jobs/settle-formal-codex-3rd` and `jobs/probe-normal-codex`, run
serially, no exceptions.

| Trial | Reward | Verifier checks | Modules changed |
|---|---|---|---|
| `settlement-netting-repair__reXoTtT` | **0.0** | 1 / 6 | 4 of 4 |
| `settlement-netting-repair__pyrFkvH` | **0.0** | 1 / 6 | 4 of 4 |
| `settlement-netting-repair__H3kwFcU` | **0.0** | 1 / 6 | 4 of 4 |
| `settlement-netting-repair__kUWUdL2` | **0.0** | 1 / 6 | 4 of 4 |

### Adversarial trial

Job `jobs/cheat-v2-codex`. The adversarial turn is terminated server-side by the model provider before
the agent completes an attack:

```
{"type":"error","message":"This content was flagged for possible cybersecurity risk. ...
 To get authorized for security work, join the Trusted Access for Cyber program"}
{"type":"turn.failed", ...}
```

The rejection concerns the red-team prompt, not the account, the task or the environment: the same
account, model and flags ran this same task to completion at the same time when the prompt was not
prepended - that run is the fourth standard trial recorded above.

`/logs/verifier/reward.json` was absent in every run, and no attempt produced a nonzero reward. Where
the verifier still executed - it runs in its own container after the agent's is destroyed - the reward
it wrote was `0`.

A turn ended by the model provider is neither the task defeating the model nor the model defeating the
task. The task's anti-cheat property does not rest on it. It rests on the Claude adversarial trial
above and on the deterministic cheat oracle below.

## Failure analysis

Seven valid trials across both models. Every one changed all four defective modules, and every one
scored zero. They also failed identically: the first mismatch is the same in all seven.

```
single batch: payment 0 is  {"amount": 4497631, ... "payer": "BKA", "payee": "INTA"}
              expected      {"amount": 8995262, ...}
```

Payer, payee and currency are right. The amount is exactly half.

Each posting is booked from both sides, so `(A,B,ccy)` and `(B,A,ccy)` are one debt seen twice. The
contract states the rule directly: *"the two directions of a pair collapse into a single obligation."*
Collapsing means adding the two records; every run instead kept one of them and discarded the other.
Three variants of the same mistake appear:

| Variant | Runs | What it does |
|---|---|---|
| `if account == left: net[key] = amount` | 5 | keeps only the record whose account sorts first |
| `if key in net: continue` then take one side's value | 1 | first writer wins, the mirror is skipped |
| negate the mirror, then `if account == left or key not in net` | 1 | gets the sign right, still assigns instead of accumulating |

The third is the most telling. That run worked out that the mirrored view carries the opposite sign -
it understood there are two views of one relationship - and still wrote `=` where `+=` was required.

Both models repaired the other three defects correctly, including choosing `toward_zero` from the four
helpers in `rounding.py` and moving fee accrual onto gross. Both also wrote a correct order-independent
`canonical_pair` helper. The failure is not a failure to read the contract or to locate the defects. It
is a single semantic judgement - fold versus deduplicate - made without any feedback that would reveal
it was wrong.

That is the property the coupling enumeration above was built to guarantee. Fifteen of sixteen repair
subsets score zero, so repairing three defects out of four looks exactly like repairing none. Nothing in
the environment tells an agent that half the money is missing.

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
