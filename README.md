# Terminal-Bench task: Order Gateway Recovery

An original Terminal-Bench task built for a hiring evaluation. The task asks an agent to repair a crash-safe
exchange order gateway so that it keeps exactly-once order effects and correct durable session state across
disconnects, retransmission, inbound sequence gaps, process restarts and concurrent workers — while staying
inside a stated transmission-call budget against the venue session.

- Task: [`tasks/order-gateway-recovery/`](tasks/order-gateway-recovery/)
- Instruction: [`tasks/order-gateway-recovery/instruction.md`](tasks/order-gateway-recovery/instruction.md)
- Normative contract: [`tasks/order-gateway-recovery/environment/docs/protocol.md`](tasks/order-gateway-recovery/environment/docs/protocol.md)
- Reviewer notes: [`tasks/order-gateway-recovery/README.md`](tasks/order-gateway-recovery/README.md)
- Design and experiment records: [`doc/`](doc/)

## Reproducing

Upstream baseline: `harbor-framework/terminal-bench` @ `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`.
Harness: Harbor `0.18.0`, Docker backend. Copy `tasks/order-gateway-recovery` into a checkout of that commit and
run the commands below from the checkout root.

```bash
# Static checks (22 at this baseline)
for check in scripts/checks/check-*.sh; do bash "$check" tasks/order-gateway-recovery; done

# Oracle: must score 1.0
harbor run -p tasks/order-gateway-recovery --agent oracle --env docker --yes --job-name oracle

# Oracle stability: ten sequential attempts, all must score 1.0
harbor run -p tasks/order-gateway-recovery --agent oracle --env docker --yes -k 10 -n 1 --job-name oracle-stability

# Nop: must score 0.0
harbor run -p tasks/order-gateway-recovery --agent nop --env docker --yes --job-name nop

# Implementation rubric (35 criteria at this baseline)
harbor check tasks/order-gateway-recovery -r docs/prompts/task-implementation.toml
```

Harbor derives its Compose project name from the task's `environment/` directory, so it is always `environment`.
Confirm no stale `environment-*` container is running before a run, otherwise the job hangs after
`Collecting main service artifacts`.

## Check results

| Check | Command | Result |
|---|---|---|
| Static checks | `scripts/checks/check-*.sh` | 22 / 22 pass |
| Docker build | part of every harbor run below | pass |
| Oracle | `--agent oracle` | reward 1.0, 17 / 17 verifier checks |
| Oracle stability | `--agent oracle -k 10 -n 1` | PENDING_STABILITY |
| Nop | `--agent nop` | PENDING_NOP |
| Cheat oracle | `cheat/solve.sh` installed as the solution | PENDING_CHEAT_ORACLE |
| Implementation rubric | `harbor check` | PENDING_RUBRIC |

## Verifier bound calibration

The only inequality-based check is the transmission-call budget. It was calibrated against implementations other
than the reference solution:

| Variant | Verifier result |
|---|---|
| Reference solution, batches of 50 | 17 / 17 pass |
| Functionally correct, one call per request | fails the budget gate and the interrupted-batch gate |
| Functionally correct, batches of ten | fails the budget gate only |

The third row is the fairness check: it shows the interrupted-batch scenario does not depend on the batch size a
gateway chooses, because the venue's prefix fault counts accepted requests rather than a position inside one call.

## Standard agent trials

Configuration taken from the baseline's `.github/harbor-run-defaults.yml`: three trials per agent,
`claude-code` on `anthropic/claude-opus-5` at `reasoning_effort=max` with `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`,
and `codex` on `openai/gpt-5.6-sol` at `reasoning_effort=xhigh`.

PENDING_STANDARD_TRIALS

## Adversarial trials

PENDING_CHEAT_TRIALS

## Failure analysis

PENDING_FAILURE_ANALYSIS

## Security

No API keys, OAuth tokens or model credentials belong in this repository.
