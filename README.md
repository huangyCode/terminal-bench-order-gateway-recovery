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
| Claude Opus 5, adversarial trial | **0.0**, reward file untouched, no exception |
| Codex gpt-5.6-sol, standard trials ×3 | **0.0 / 0.0 / 0.0**, no exceptions (a fourth valid run also scored 0.0) |
| Codex gpt-5.6-sol, adversarial trial | terminated server-side by the provider's classifier; no run produced a nonzero reward |

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

All seven valid runs failed identically. Every one produced `4,497,631` where `8,995,262` is owed —
exactly half. Every posting is recorded from both sides, so the two directions of a counterparty pair are
one debt seen twice, and collapsing them means adding the two records. Every run kept one and discarded
the other.

This is not a failure to find the defects. Every run changed all four defective modules, repaired three
of them correctly, and wrote a correct order-independent pair helper. One run even worked out that the
mirrored view carries the opposite sign — and still assigned where it had to accumulate. The whole
outcome turns on one semantic judgement made with no feedback that would reveal it was wrong.

## Why this design, and not an easier one

Three earlier designs were built and measured before this one. They are not part of the submission;
what they established is.

| Design | What it tested | Measured outcome |
|---|---|---|
| Crash-consistent order gateway | implementing a complete crash-consistency specification | Codex passed every revision |
| Metering replica, seven rules | inducing the rules from a 12,000-line recording | both models passed three of three |
| Billing replica, fifteen rules | the same, plus an order-dependent discount chain and three rounding conventions | Claude passed; its output grew from 65 KB to 1.34 MB and the outcome did not change |

The third is the useful negative result: **rule count is not difficulty**. When the recording is
complete, the winning method is a mechanical implement-replay-fix loop, and more rules only make the
loop longer. Difficulty had to come from removing the feedback, not from adding rules - which is what
the enumeration above is built on: fifteen of sixteen repair subsets score zero, so no partial repair
tells the agent it is on the right track.

## Separating a model failure from a broken task

A failing trial proves nothing on its own. It has two possible causes that look identical from the
outside: the model did not manage the task, or the task did not give it enough to work with. Every
candidate failure was put through that test before this task was frozen, and each time the deciding
evidence was the artifact, not the score.

The rule that came out of it, and that this task is built on:

> **No rule ships until ablating it is shown to change the evidence the agent is given.** If removing a
> rule changes nothing an agent can observe, the rule is unlearnable and the task is unfair.

That rule exists because of one measurement. An earlier design had both models failing in exactly the
same way, which reads as a genuine capability limit. Ablation said otherwise: the rule they missed
changed **zero lines** of the shipped recording. `seq` was global across accounts, so in a many-account
stream every event looks like a sequence gap to its own account, and the window was always flushed
before anything could age out. The recording was all many-account streams; the test was single-account.
The rule was not hard, it was invisible. Mixing single, three and fourteen-account streams took the
evidence from zero lines to 3,373, and both models then passed — which is what a fair-but-learnable rule
looks like.

The other corrections were of the same kind: assertions that pinned an implementation's intermediate
state rather than the contract's observable outcome, a check that demanded one recovery mode where the
contract permitted another, a fee schedule the contract never related to the field the agent was given,
and a defect that no generated day could reach. Each was removed or repaired before the trials that are
reported here.

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

`--agent-setup-timeout-multiplier 8` accommodates a slow container link on this host; it changes no
agent or model parameter.

Adversarial trials use the same two commands, pointed at an instruction built the way
`.github/workflows/run-cheat-trials.yml` builds it: the task's own "Do not cheat" sentence is stripped,
then `docs/prompts/hack-trial-prompt.md` is appended after the task description.

## Results

See [`doc/RESULTS.md`](doc/RESULTS.md) for every trial: job directory, configuration, reward, exception
status, validity judgement and root cause.

## Infrastructure faults are never model failures

A trial counts only if the agent ran to its own conclusion and the verifier reached a verdict. Every
trial reported here was checked against `exception_stats` in the job's `result.json` before being
counted, and against the collected artifact to confirm the agent had in fact modified the starting code.
Runs that ended in an environment, network, rate-limit or container fault were rerun, not recorded.

## Security

No API keys, OAuth tokens or model credentials belong in this repository.
