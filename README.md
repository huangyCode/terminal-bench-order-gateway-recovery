# Terminal-Bench 3 task submission

Original Terminal-Bench 3 tasks built for a hiring evaluation, together with the full record of how they
were designed, where the designs failed, and how each failure was diagnosed.

Upstream baseline: `harbor-framework/terminal-bench` @ `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`.
Harness: Harbor `0.18.0`, Docker backend.

## Tasks

| Task | Domain | State |
|---|---|---|
| [`billing-discount-replica`](tasks/billing-discount-replica/) | Legacy modernization — recover a retired billing engine from a recording of its traffic | current candidate |
| [`legacy-billing-replica`](tasks/legacy-billing-replica/) | Same shape, seven rules instead of fifteen | superseded; kept as the difficulty control |
| [`order-gateway-recovery`](tasks/order-gateway-recovery/) | Crash-safe exchange order gateway | superseded; kept as the first design line |

## What this submission is really about

The hiring brief asks for a task that two frontier agents fail six times out of six. Reaching that bar
turned out to be the smaller part of the work. The larger part was telling a genuine model failure apart
from a defect in my own task, and four times in one day a result that looked like a model failure was not
one. Each is documented with the artifact that disproved it:

1. Seven assertions required `sync` to report `caught_up=false` after a lost response. Codex's artifact
   re-read the authoritative session and converged inside the same call, which the contract permits — the
   assertions were demanding the reference solution's implementation choice.
2. Two assertions pinned intermediate state that depends on the gateway not retrying inside a call.
3. One assertion demanded `REPLAY` for a sequence whose acceptance the gateway had legitimately recorded
   earlier, where the contract calls for `GAP_FILL`. Replaying Codex's artifact without that assertion:
   17/17.
4. Both models failed the legacy replica identically. Ablation showed the rule they missed changed **zero**
   lines of the shipped recording — it was unlearnable, so the failure did not count. `seq` is global
   across accounts, so in a many-account stream every event looks like a sequence gap to its own account
   and the window is flushed before anything can age out. The recording was all many-account streams; the
   test was single-account.

The fourth was raised by a reviewer asking whether the failure might be missing information rather than
missing capability. That question is now a standing procedure: **no rule ships until ablating it is shown
to change the recording.**

[`doc/DESIGN-ITERATIONS-2026-09-14.md`](doc/DESIGN-ITERATIONS-2026-09-14.md) carries the full account.

## Verifier security finding

The `cheat/` oracle forged a passing reward on its first run, while 22 static checks, the oracle and the
nop validation were all green. The defence in place was `chmod 700 /logs/verifier` — the measure the
implementation rubric itself recommends. It works on an overlay filesystem and silently does nothing on a
bind-mounted logs directory, so the unprivileged daemon could write the verdict. The proof is the
existence of `reward.json`, a file `test.sh` never creates.

The verdict is now written by root only after every process belonging to the unprivileged user has been
reaped and anything planted in the reward directory has been deleted. Any verifier that executes
agent-produced code and relies on that chmod alone is bypassable on at least one supported backend.

## Reproducing

```bash
# Static checks
for check in scripts/checks/check-*.sh; do bash "$check" tasks/billing-discount-replica; done

# Oracle must score 1.0, nop must score 0.0
harbor run -p tasks/billing-discount-replica --agent oracle --env docker --yes
harbor run -p tasks/billing-discount-replica --agent nop    --env docker --yes

# Implementation rubric
harbor check tasks/billing-discount-replica -r docs/prompts/task-implementation.toml

# Ground truth provenance: the verifier's Python replica vs the original compiled engine
python3 tasks/billing-discount-replica/tests/validate_reference.py
```

Harbor derives its Compose project name from the task's `environment/` directory. Clear any stale
`environment-*` container before a run, otherwise the job hangs after `Collecting main service artifacts`.

## Results

RESULTS_PENDING

## Infrastructure faults are never model failures

Every trial is checked against `exception_stats` before it is counted. Faults seen and diagnosed during
this work, all discarded rather than recorded as failures:

| Symptom | Root cause |
|---|---|
| `EnvironmentStartTimeoutError` ×6 | All three configured Docker registry mirrors unreachable; image pulls hung instead of failing |
| harbor hanging before writing any log line | Orphaned `docker compose` / `buildx bake` children left by those hangs |
| `AgentSetupTimeoutError` | nodejs.org throughput varying between 41 KB/s and 1.6 MB/s |
| Three codex trials idle for an hour | `failed to refresh available models`; `api.openai.com` unreachable from host and container |

## Security

No API keys, OAuth tokens or model credentials belong in this repository.
