# Terminal-Bench 3 task submission

Four original Terminal-Bench 3 tasks and the record of how they were designed, where the designs failed,
and how each failure was diagnosed.

Upstream baseline: `harbor-framework/terminal-bench` @ `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`.
Harness: Harbor `0.18.0`, Docker backend. Agent and model configuration taken from that commit's
`.github/harbor-run-defaults.yml`.

## The submitted task

[`tasks/settlement-netting-repair`](tasks/settlement-netting-repair/) — a multi-currency settlement
pipeline that no longer agrees with the clearing counterparty. Four defects sit in four modules at four
layers, and the agent is told neither where they are nor how many there are.

| Check | Result |
|---|---|
| Static checks | 22 / 22 |
| Docker build | pass |
| Oracle | reward 1.0, 6 / 6 verifier checks |
| Nop | reward 0.0 |
| Implementation rubric | `difficult`, `essential_difficulty`, `novel`, `interesting`, `agentic`, `anti_cheat_robustness`, `deterministic_reproducible`, `solvable`, `verifiable`, `test_instruction_alignment` all pass |
| Claude Opus 5, standard trials ×3 | **0.0 / 0.0 / 0.0**, no exceptions |
| Claude Opus 5, adversarial trial | **0.0** after thirty minutes under the red-team prompt |
| Codex gpt-5.6-sol | see Results |

### Why it is hard

Not because the rules are hidden — `environment/docs/settlement.md` states all four:

> A reversal may name a transaction from any earlier batch as well as its own.
> The two directions of a pair collapse into a single obligation.
> Fees follow the traffic that was processed, not what survives netting.
> Conversion truncates toward zero.

It is hard because **there is no partial credit and no partial signal**. All sixteen repair subsets were
enumerated against three generated days: fifteen produce zero passing checks, and only the complete
repair passes. Fixing three defects of four looks exactly like fixing none — five red checks either way.
The loop every agent relied on in the earlier designs, *change something and watch the score move*, has
nothing to climb.

Claude's three failures are identical: each repaired only the rounding module and each produced
`4,497,631` where `8,995,262` is owed. Every posting is recorded from both sides, so the two directions
of a counterparty pair are one debt seen twice; the model treated them as two debts that offset.

## The other three tasks

Kept because they are the measurements that led here, not because they are submissions.

| Task | What it tested | Outcome |
|---|---|---|
| [`order-gateway-recovery`](tasks/order-gateway-recovery/) | implementing a complete crash-consistency spec | Codex passed all six revisions |
| [`legacy-billing-replica`](tasks/legacy-billing-replica/) | inducing seven rules from a 12,000-line recording | both models passed three of three |
| [`billing-discount-replica`](tasks/billing-discount-replica/) | the same with fifteen rules and an order-dependent discount chain | Claude passed; output grew from 65 KB to 1.34 MB and the outcome did not change |

The third is the useful negative result: **rule count is not difficulty**. With a complete recording the
winning method is a mechanical implement-replay-fix loop, and more rules only make the loop longer.

## Telling a model failure from a broken task

Six times a result looked like a model failure and was not. Each is documented with the artifact that
disproved it:

1. Seven assertions demanded `sync` report `caught_up=false` after a lost response. Codex's artifact
   re-read the authoritative session and converged inside the same call, which the contract permits.
2. Two assertions pinned intermediate state that only holds if the gateway does not retry inside a call.
3. One assertion demanded `REPLAY` for a sequence whose acceptance the gateway had legitimately
   recorded, where the contract calls for `GAP_FILL`. Replaying that artifact without the assertion: 17/17.
4. Both models failed the legacy replica identically. Ablation showed the rule they missed changed
   **zero** lines of the shipped recording — `seq` is global across accounts, so in a many-account stream
   every event looks like a sequence gap to its own account and the window is flushed before anything can
   age out. The recording was all many-account streams; the test was single-account.
5. Claude's first run on this task raised `KeyError: 'swap'`, reading the fee schedule from an entry's
   `product` field. The contract never related that field to the schedule names.
6. A defect in an early revision of this task was unreachable: `obligations()` normalises direction, so
   negative rounding was never exercised. A defect no check can observe is a hidden requirement, so the
   report gained a signed per-account residual and the enumeration was rerun.

The fourth was raised by a reviewer asking whether the failure might be missing information rather than
missing capability. That question is now a standing procedure: **no rule ships until ablating it is shown
to change the evidence the agent is given.**

## Verifier security finding

The `cheat/` oracle forged a passing reward on its first run while 22 static checks, the oracle and the
nop validation were all green. The defence in place was `chmod 700 /logs/verifier` — the measure the
implementation rubric itself recommends. It works on an overlay filesystem and silently does nothing on a
bind-mounted logs directory. The proof is the existence of `reward.json`, a file `test.sh` never creates.

The verdict is now written by root only after every process belonging to the unprivileged user has been
reaped and anything planted in the reward directory has been deleted. Any verifier that executes
agent-produced code and relies on that chmod alone is bypassable on at least one supported backend.

## Reproducing

```bash
# Static checks
for check in scripts/checks/check-*.sh; do bash "$check" tasks/settlement-netting-repair; done

# Oracle must score 1.0, nop must score 0.0
harbor run -p tasks/settlement-netting-repair --agent oracle --env docker --yes
harbor run -p tasks/settlement-netting-repair --agent nop    --env docker --yes

# Implementation rubric
harbor check tasks/settlement-netting-repair -r docs/prompts/task-implementation.toml

# Standard trials, configuration from .github/harbor-run-defaults.yml
harbor run -p tasks/settlement-netting-repair \
  --agent claude-code --model anthropic/claude-opus-5 \
  --env docker --yes --ae CLAUDE_FORCE_OAUTH=1 --ae CLAUDE_CODE_OAUTH_TOKEN=<token> \
  --ae CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 --ak reasoning_effort=max \
  --agent-setup-timeout-multiplier 8 -k 3 -n 3 -r 3

harbor run -p tasks/settlement-netting-repair \
  --agent codex --model openai/gpt-5.6-sol \
  --env docker --yes --ae CODEX_FORCE_AUTH_JSON=1 --ak reasoning_effort=xhigh \
  --agent-setup-timeout-multiplier 8 -k 3 -n 3 -r 3
```

Two notes for anyone rerunning this. Harbor derives its Compose project name from the task's
`environment/` directory, so clear any stale container of that name first or the job hangs after
`Collecting main service artifacts`. And `harbor check` has no setup-timeout flag while `harbor run`
does, so on a slow link the rubric fails where trials succeed — with `-a codex` the two setup commands
measured 414 s against a 360 s hard limit, because the first installs Node through apt and the second
installs it again through nvm.

## Results

See [`doc/RESULTS.md`](doc/RESULTS.md) for every trial: job directory, configuration, reward, exception
status, validity judgement and root cause.

## Infrastructure faults are never model failures

Every trial is checked against `exception_stats` before it is counted. Faults diagnosed during this work,
all discarded rather than recorded:

| Symptom | Root cause |
|---|---|
| `EnvironmentStartTimeoutError` ×6 | All three configured Docker registry mirrors unreachable; image pulls hung instead of failing |
| harbor hanging before writing any log line | Orphaned `docker compose` / `buildx` children left by those hangs |
| `AgentSetupTimeoutError` | Agent bootstrap throughput varying between 6.8 KB/s and 1.46 MB/s across the day |
| Three codex trials idle for an hour | `failed to refresh available models`; `api.openai.com` unreachable from host and container |
| Two codex trials scoring 0.0 with 774-byte transcripts | Account usage limit reached; the artifact was the unmodified starting code |

## Security

No API keys, OAuth tokens or model credentials belong in this repository.
