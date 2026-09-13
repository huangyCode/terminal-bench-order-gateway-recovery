# Development trial log

## Trial D1 — Codex on the vertical prototype

- Date: 2026-09-13
- Task revision: uncommitted vertical prototype on `task/order-gateway-recovery`
- Harness: Harbor 0.18.0, Docker backend
- Agent: `codex`
- Model: `openai/gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Job: `jobs/2026-09-13__00-34-53`
- Runtime: 10m 19s
- Reported reward: 0.0
- Infrastructure status: valid; no agent/container/API exception
- Classification: **invalid model failure; functionally solved**

### Evidence

Codex identified the intended durable-session defects, implemented a transactional SQLite inbox/outbox, durable execution-ID deduplication, persistent gap buffering, ordered replay, stable outbound identities, validation, rollback, and deterministic ordering. Seven functional verifier cases passed.

The sole failed verifier case rejected a `.pyc` file under the submitted gateway tree. Codex had created it through the normal engineering action `python3 -m py_compile gateway/*.py`. The instruction neither prohibited bytecode cache files nor required a source-only tree. Therefore the zero reward was caused by an over-restrictive verifier assertion, not a meaningful model failure.

### Corrective action

- Removed the suffix assertion that allowed only `.py` files.
- Retained symlink rejection and a generous total artifact-size ceiling as anti-abuse safeguards.
- Do not count this run toward any required standard trial.
- Treat the prototype as too easy: a frontier agent repaired the complete functional surface in one valid attempt.

### Design implication

The vertical prototype validates the process-isolated verifier and crash/restart testing approach, but its small synchronous JSON-RPC surface is not TB3-level. The next revision must add genuine system depth—an independent network peer, request-chain semantics, outbound replay/gap-fill behavior, and crash points spanning transport and business acknowledgement—without manufacturing difficulty through undocumented file restrictions.

## Validation V2a — independent venue and ambiguous commit

- Date: 2026-09-13
- Harness: Harbor 0.18.0, Docker backend
- Scope: first networked increment (`NEW` plus session reconciliation)
- Static checks: all 22 checks from `.github/workflows/static-checks.yml` passed
- Docker build: gateway and venue images passed
- Oracle job: `jobs/2026-09-13__01-35-20`, reward 1.0, no exception
- Nop job: `jobs/2026-09-13__01-35-48`, reward 0.0, no exception

### Deterministic fault result

The venue was configured to commit one NEW request and close the connection before writing its HTTP response. The first gateway `sync` returned `caught_up=false` while retaining the identical durable outbound message. A second `sync` read the venue session history, applied the recorded acknowledgement, and returned `caught_up=true`; the local outbox became empty and the venue contained one business order effect.

This is an implementation checkpoint, not a required model trial. Standard and adversarial trials remain pending until the complete request-chain verifier is frozen.

## Validation V2b — durable NEW/REPLACE/CANCEL chain

- Date: 2026-09-13
- Static checks: all 22 current CI checks passed
- Oracle: `jobs/2026-09-13__01-41-08`, reward 1.0, no exception
- Nop: `jobs/2026-09-13__01-41-38`, reward 0.0, no exception
- Verifier boundary: a private venue process is started inside the separate verifier container and is not reachable as an artifact or control surface from the agent container

The scenario durably queues a NEW followed by REPLACE and CANCEL, kills the gateway before the latter requests are synchronized, restarts it against the same independent venue, and compares normalized local state with the venue's authoritative ledger. Two earlier Oracle attempts (`01-38-52`, `01-39-48`) exposed test-environment assumptions during development and are not trial results: the first encountered a stale public sidecar session; the second proved that a separate verifier intentionally cannot resolve the agent-side Compose hostname. Both were corrected by moving the authoritative test peer into the verifier boundary.

## Validation V2c — ambiguous commits and verifier process hygiene

- Date: 2026-09-13
- Oracle stability: `jobs/2026-09-13__09-51-09`, 3/3 reward 1.0, zero exceptions
- Nop: `jobs/2026-09-13__09-52-21`, reward 0.0, zero exceptions
- Additional invariant: NEW and REPLACE are each committed by the venue before its HTTP response is deliberately dropped; the gateway is killed after each ambiguous result and must recover without adding a duplicate venue request.
- Isolation hardening: every gateway subprocess starts in its own process group, and the verifier kills that group after crash and graceful-stop scenarios.

The implementation-rubric attempt at `jobs/2026-09-13__09-49-40` is invalid infrastructure output: Claude Code returned `authentication_failed` and `Not logged in` before reading the task, producing no criterion verdicts. It is not classified as a task failure and must be rerun after Claude authentication is configured.

## Trial D2 — Codex on the networked request-chain task

- Date: 2026-09-13
- Task revision: V2c (`bb89f84` in the submission repository)
- Harness: Harbor 0.18.0, Docker backend
- Agent/model: Codex, `openai/gpt-5.6-sol`, reasoning `xhigh`
- Job: `jobs/codex-v2c-calibration`
- Runtime: 20m 26s
- Reward: 1.0
- Exceptions: 0
- Classification: valid legitimate pass; development calibration only

Codex implemented durable inbound normalization, transactional replay, stable request chains, send-attempt tracking with `poss_dup`, session reconciliation, and restart repair. All ten verifier cases passed. The run consumed substantial exploration and reasoning, but it proves this revision cannot meet the hiring requirement that all three standard trials fail.

### Design implication

Do not count or present D2 as a required failure. The next revision must exercise recovery decisions that cannot be handled by simply replaying the venue's full response history: explicit venue-requested outbound resend ranges, gap fills for already accepted sequence slots, and inbound replay where the same business execution arrives under a new session sequence. These extend the same session-recovery problem rather than adding unrelated surface area.

## Validation V3a — resend ranges and durable send attempts

- Date: 2026-09-13
- Static checks: all 22 current CI checks passed
- Oracle: `jobs/2026-09-13__10-19-16`, reward 1.0, zero exceptions
- Nop: `jobs/2026-09-13__10-20-14`, reward 0.0, zero exceptions

The verifier now distinguishes two outbound recovery decisions. A locally acknowledged sequence must be represented as a GAP_FILL during venue-requested recovery, while a venue-accepted request whose response was hidden from the recovering gateway must be replayed byte-for-semantics with its original sequence and identity. A separate pre-commit disconnect requires the gateway to have durably recorded the send attempt before I/O, so its post-restart retry sets `poss_dup=true` even though the venue has no business effect yet.

## Trial D3 — Codex on outbound recovery V3a

- Date: 2026-09-13
- Task revision: V3a (`39d80fb` in the submission repository)
- Agent/model: Codex, `openai/gpt-5.6-sol`, reasoning `xhigh`
- Valid job: `jobs/codex-v3a-calibration-retry`
- Runtime: 27m 49s
- Reward: 1.0
- Exceptions: 0
- Classification: valid legitimate pass; development calibration only

The preceding job `jobs/codex-v3a-calibration` produced zero valid trials because NVM/npm installation exceeded Harbor's 360-second agent-setup timeout. It is an infrastructure error and is not counted. The retry changed only the local setup-timeout multiplier and then completed normally.

Codex's valid pass shows that explicit outbound replay, gap-fill selection, and durable pre-I/O attempt tracking add meaningful work but still do not meet the required frontier-model failure rate. V3b must add the other half of session recovery: independently sequenced inbound events, durable future-event buffering, missing-range reconciliation, and repeated business executions under new delivery sequence numbers.

## Validation V3b — inbound delivery gaps and replay

- Date: 2026-09-13
- Static checks: all 22 current CI checks passed
- Oracle: `jobs/2026-09-13__14-52-20`, reward 1.0, zero exceptions
- Nop: `jobs/2026-09-13__14-53-10`, reward 0.0, zero exceptions

The venue now keeps its accepted-request ledger separate from its event-delivery log. The verifier hides venue sequence 2 while delivering sequence 3, where sequence 3 repeats the stable business `exec_id` from sequence 1. It kills the gateway with the future event buffered, restores sequence 2, restarts the gateway, and requires the contiguous delivery cursor to reach 4 while applying the repeated business event only once.

The first Oracle attempt (`jobs/2026-09-13__14-50-50`) exposed a reference-solution bug: `sync` compared its inbound cursor with the session snapshot taken before sending new requests. The fix performs a final session refresh after outbound progress. This was an implementation-development failure, not a model trial.

## Trial D4 — Codex on bidirectional recovery V3b

- Date: 2026-09-13
- Task revision: V3b (`54112a6` in the submission repository)
- Agent/model: Codex, `openai/gpt-5.6-sol`, reasoning `xhigh`
- Job: `jobs/codex-v3b-calibration`
- Runtime: approximately 41m 37s
- Reward: 1.0
- Exceptions: 0
- Verifier: 13/13 tests passed
- Classification: valid legitimate pass; development calibration only

Codex successfully unified outbound request recovery with independently sequenced inbound delivery buffering and stable execution-ID deduplication. The longer trajectory confirms meaningful agentic work, but duration is not a failure signal and the pass means V3b still cannot satisfy the required three failures per model.

The next difficulty increment should introduce a single realistic systems boundary not covered by more sequential schedules: two gateway processes sharing the durable database and racing submit/sync/recovery operations. Correctness then requires transaction-level sequence allocation, bounded SQLite lock handling, and prevention of double-send across concurrent workers while preserving every existing crash invariant.
