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

## Validation V3c — concurrent shared-database workers

- Date: 2026-09-13
- Static checks: all 22 current CI checks passed
- Initial Oracle: `jobs/2026-09-13__15-41-30`, reward 1.0
- Stability discovery: `jobs/2026-09-13__15-42-44`, only 2/5 Oracle passes
- Corrected stability run: `jobs/2026-09-13__15-46-12`, 5/5 reward 1.0, zero exceptions
- Nop: `jobs/2026-09-13__15-52-58`, reward 0.0, zero exceptions

Two gateway processes concurrently submit disjoint client intents into one SQLite database, then concurrently synchronize against one venue. The verifier requires 16 unique gap-free client sequences, one venue effect per order, convergence after one worker is killed, and identical normalized state from the survivor.

The first repeated Oracle run exposed a real bootstrap race: a worker could exit while both processes configured SQLite WAL/schema state. The store now retries only SQLite busy/locked bootstrap failures, uses a bounded timeout, and begins mutation transactions with `BEGIN IMMEDIATE`. Five consecutive corrected Oracle trials passed; the earlier 2/5 result is retained as development evidence and is not a model trial.

## Trial D5 — Codex on concurrent shared-database workers V3c

- Date: 2026-09-13
- Task revision: V3c (`d92266b` in the submission repository)
- Agent/model: Codex, `openai/gpt-5.6-sol`, reasoning `xhigh`
- Job: `jobs/codex-v3c-calibration`
- Runtime: 43m 03s
- Reward: 1.0
- Exceptions: 0
- Classification: valid legitimate pass; development calibration only

Codex repaired the full request and inbound-session state machines and handled the shared-database schedule by combining `BEGIN IMMEDIATE` mutation transactions with a process-scoped `flock` around network reconciliation. The kernel releases that lock if its owner dies, while concurrent callers return a retryable result instead of double-sending. The agent also built its own protocol, disconnect, restart, resend, and real-HTTP concurrency tests before the hidden verifier passed.

This is not a required standard trial and must not be reported as a model failure. V3c increased solution time substantially but still allowed concurrency to be reduced to one globally serialized `sync`. V3d should test a deterministic handoff across the dangerous network window: kill the active coordinator after the independent venue has durably committed but before its response is delivered, accept additional intents through another worker, and require that survivor to reconcile the ambiguous old request, outbound resend state, and an inbound delivery gap before sending the new suffix exactly once.

## Validation V4 — batched reconciliation with a deterministic transmission budget

- Date: 2026-09-14
- Harness: Harbor 0.18.0, Docker backend
- Upstream baseline: `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`

### Why the axis changed

Four consecutive increments (V2c, V3a, V3b, V3c) were validly passed by Codex, and reading the artifact from
`jobs/codex-v3c-calibration` explained why. Its `store.py` implements `sync_lock()` as a non-blocking
`fcntl.flock`, used only around network reconciliation, with the comment that the kernel releases it when a
process dies. Client intent is appended under SQLite `BEGIN IMMEDIATE` and does not take that lock. That design
already satisfies every barrier V3d was built to test, so V3d would very likely have been passed as well.

A fencing/epoch increment was designed and then discarded before implementation: `apply_request` in the venue
already returns the recorded response for a known `request_id` without creating a second effect, and requires
`client_seq` to equal `next_client_seq` exactly. A resumed zombie worker therefore cannot double-apply anything,
so an epoch check would have added protocol surface without adding difficulty.

V4 changes the kind of difficulty instead of adding another invariant of the same kind. Correctness is no longer
sufficient: the venue session carries a stated transmission-call budget, so reconciliation must batch, and
batching is what makes the failure cases harder. An interrupted batch leaves a durable prefix whose length cannot
be determined from local state, so efficiency and crash-consistency pull against each other.

### Implementation

- Both venues gained `POST /requests` (ordered batch, at most 50, per-request commit), a `transmit_calls` counter
  exposed at `GET /stats`, and an `accept_prefix` fault that accepts a counted number of requests and then drops
  the connection without answering.
- Disconnect faults were refactored into a shared `transmit_one` helper so a scenario behaves identically whether
  the gateway transmits singly or in a batch. Before the refactor, batching silently disabled five existing
  scenarios (observed as 12/17 in `jobs/oracle-v4a`).
- The reference solution transmits the contiguous unacknowledged prefix as one batch, durably marks every message
  in it as attempted before any I/O, and re-reconciles from the venue session when the venue stops early.
- Two verifier gates were added: a 200-request backlog capped at six transmission calls, and an interrupted batch
  (17 of 60 accepted) followed by a kill, restart and recovery with no duplicate or skipped sequence.

### Verifier hardening applied in the same pass

- `tests/test.sh` no longer pre-writes `reward.txt`, and only pytest exit codes 0 and 1 are gradeable. Collection
  or internal errors, and a verifier venue that will not start, leave the reward unwritten so the harness records
  an infrastructure error instead of a zero the agent did not earn. Regression: `jobs/oracle-t2t3-regression`,
  5/5 reward 1.0.
- Gateway diagnostics are captured to a temp file instead of a pipe, closing a path where a daemonised grandchild
  holding stderr open would block the verifier until its timeout.
- A `cheat/` oracle was added following the convention used by 17 merged tasks: it installs a gateway core that
  solves nothing, double-forks a daemon that tries to overwrite `/logs/verifier/reward.*`, and holds stderr open.

### Negative calibration of the new bounds

| Variant | Result | Meaning |
|---|---|---|
| Reference solution (batch of 50) | 17/17 | minimum achievable is four calls, budget is six |
| One call per request, functionally correct | fails budget + interrupted-batch gates | correctness alone is not sufficient |
| Batches of ten, functionally correct | fails budget gate only | the interrupted-batch gate does not depend on the batch size chosen |

The third row is the important one: it confirms the `accept_prefix` fault counts accepted requests rather than a
position inside one call, so a gateway that batches differently from the reference solution is not failed for the
wrong reason. An earlier position-based version of that fault would have silently skipped the scenario for any
batch size below the prefix length; it was corrected before the bound was recorded.

### Results at this revision

- Static checks: 22/22
- Oracle smoke: `jobs/oracle-v4-smoke`, reward 1.0, 17/17 checks
- Oracle stability: `jobs/oracle-v4-stability`, see the results table in the submission README

### Infrastructure note that cost time

A first attempt at the stability run hung after `Collecting main service artifacts` with no container left
running. The cause was a `environment-venue-1` container left running for 23 hours by an earlier direct
`docker compose` session. The task's compose file lives in `environment/`, so its compose project name is
`environment` and collided with that stale project. Removing the stale container restored normal runs. This is
recorded because it is exactly the class of failure that must never be counted as a model failure.

## Security finding V4-S1 — the reward channel was forgeable through a bind-mounted logs directory

- Date: 2026-09-14
- Found by: the newly added `cheat/` oracle, on its first run
- Job (exploited): `jobs/cheat-oracle-v4`, reward **1**
- Job (blocked after the fix): `jobs/cheat-oracle-v4-hardened`, reward **0**

### What happened

The cheat oracle installs a gateway core that solves nothing and, at import time, double-forks a daemon which
repeatedly writes a passing verdict to `/logs/verifier/reward.txt` and `/logs/verifier/reward.json`. The verifier
ran it as `nobody` through `runuser`, the tests failed 16 of 17, `test.sh` wrote `0` — and the job still reported
reward **1**. `reward.json` is proof on its own: `test.sh` never creates that file, so it could only have been
written by the executed artifact.

### Root cause

The defence was `chmod 700 /logs/verifier` before any agent code runs. In a bare container that works: probing the
verifier image directly, `runuser -u nobody -- sh -c 'echo 1 > /logs/verifier/reward.txt'` returns
`Permission denied`. In a real trial the same directory is bind-mounted from the macOS host, where Docker
Desktop's file sharing does not honour a container-side `chmod`, so the mode never took effect and the
unprivileged daemon could write. A verdict that depends on directory permissions is therefore not portable across
environment backends.

### Fix

`tests/test.sh` no longer relies on the reward directory's mode. The verdict is now produced by root, after the
verifier has reaped everything the agent produced:

1. pytest writes its CTRF report to `/tmp/ctrf.json`, outside the reward directory, while agent code is alive.
2. After pytest returns, `pkill -9 -u nobody` runs three times with a short pause. The gateway only ever executes
   as `nobody`, so this reaps any daemon that outlived its session and is waiting to forge a verdict.
3. Root deletes `reward.txt` and `reward.json` — discarding anything the artifact planted — copies the CTRF report
   in, and only then writes the reward derived from pytest's own exit status.
4. `chmod 700` is kept as defence in depth but is no longer load-bearing, and is tolerant of failure.
5. `procps` was added to the verifier image for `pkill`.

### Why this matters beyond this task

The implementation rubric's `verifier_execution_isolation` guidance lists `chmod 700 /logs/verifier` as the way to
protect the reward channel. That is sufficient on an overlay filesystem and insufficient on a bind mount that
ignores chmod. Any task whose verifier executes agent-produced code and relies on that single measure is
exploitable on at least one supported backend. Killing the unprivileged processes before root states the verdict
is the portable version of the same rule.

This is also the strongest argument for the adversarial trial requirement: every automated check, the oracle, the
nop validation and all 22 static checks were green while the verifier was trivially bypassable.

## Infrastructure finding V4-I1 — the host Docker allocation, not the task, caused six errored trials

- Date: 2026-09-14
- Job: `jobs/oracle-v4h-stability` — 10 attempts, 4 scored (all reward 1.0), **6 errored**
- Exception: `EnvironmentStartTimeoutError` on every errored attempt, followed by
  `no container found for service "main"` when artifact collection ran against an environment that never started

### What it was not

An earlier hang in this session was caused by a stale `environment-venue-1` container left by a manual
`docker compose` session, and that led to the wrong conclusion that harbor reuses one Compose project. The trial
log disproves it: harbor passes `--project-name order-gateway-recovery__<trial>__env`, so every trial gets its own
project, its own containers and its own named volume. Trials do not collide with each other. A manually created
`environment` project can still collide with them, so stale containers must be cleared before a run, but that is
not what produced these six errors.

### What it was

Memory. The host Docker allocation was 7.7 GB while the task requested `memory_mb = 4096` for the main container
alone, alongside a venue sidecar, a verifier container and five unrelated long-running services on the same
daemon. The first attempts succeeded and later ones failed as pressure accumulated, which is consistent with the
venue healthcheck missing its window rather than with any nondeterminism in the task.

### Response

Two changes, in opposite directions:

1. The task's own footprint was reduced from `memory_mb = 4096` to `2048`. Nothing in the verification needs 4 GB —
   the workload is SQLite and a few small Python processes, and the largest scenario is 200 queued orders. The
   implementation rubric's `resource_configuration` criterion explicitly prefers reworking a task to use fewer
   resources when the intellectual challenge is unaffected, so this is an improvement independent of the incident.
2. The host Docker allocation must be raised before the formal trials. At 7.7 GB the results are not trustworthy
   even when run sequentially: a majority of attempts never reached the verifier.

### Discipline this reinforces

`EnvironmentStartTimeoutError` is an environment fault and is never a model failure. A standard trial that ends
this way must be discarded and rerun, and the count of valid trials must be taken from the scored attempts, not
from the number of attempts launched. The same applies to the errored attempt recorded in the earlier
`jobs/oracle-v3d-stability` run.

## Correction to V4-I1 — the six errored trials were a registry failure, not memory pressure

- Date: 2026-09-14
- Supersedes the memory explanation recorded in V4-I1 above.

### Evidence

Nine hours after the `oracle-v4h-stability` job finished, two `docker compose` invocations and two
`docker-buildx bake` invocations were still running, with elapsed times of 9h26m and 9h16m. Their project names
were `order-gateway-recovery__8vfj5kd__env` and `order-gateway-recovery__cus5vpa__env` — two of the six trials that
harbor had recorded as `EnvironmentStartTimeoutError`. They had never exited.

The reason they never exited is the host's Docker registry configuration. Three Docker Hub mirrors are configured
(`docker.1panel.live`, `docker.m.daocloud.io`, `dockerproxy.com`) and all three are unreachable:

```
dialing docker.1panel.live:443 ... connect: can't assign requested address
```

`python:3.13-slim-bookworm` was not present locally, so every environment build tried to pull it and hung
indefinitely rather than failing. Two facts confirm the diagnosis rather than the memory theory: a trivial
`docker build` from a locally cached base completed immediately, and `apt-get update` from inside a container
succeeded — so the network and the build subsystem were both healthy. Only image pulls were broken.

The hung processes also explain a second symptom: after those orphans accumulated, every new harbor run stalled
before writing a single line of its trial log, even with `--debug`. They were blocking the new runs.

### Resolution

1. The base image was fetched through a reachable mirror and tagged locally:
   `docker pull mirror.gcr.io/library/python:3.13-slim-bookworm` then
   `docker tag mirror.gcr.io/library/python:3.13-slim-bookworm python:3.13-slim-bookworm`.
   Verified as `VERSION_CODENAME=bookworm`, Python 3.13.15. No task file changed — the Dockerfiles still name the
   canonical tag, so a reviewer on a working registry pulls the real image.
2. The orphaned `docker compose` and `docker-buildx bake` processes were killed.

After both steps, nop scored 0.0 and oracle runs completed normally in under a minute each.

### What this changes about the task

Nothing. `memory_mb` was reduced from 4096 to 2048 while the memory theory was live, and that reduction is kept on
its own merits — the workload is SQLite and a handful of small Python processes, and the rubric's
`resource_configuration` criterion prefers the smaller footprint. But it was not the fix.

### Discipline

Two rules follow, both about never letting local infrastructure contaminate trial results:

1. `EnvironmentStartTimeoutError` is an environment fault. The six errored attempts in `oracle-v4h-stability` are
   discarded, not counted as oracle failures. The four attempts that reached the verifier all scored 1.0.
2. Killing a harbor run leaves orphaned `docker compose` and `buildx` children that silently block every later
   run. After interrupting a job, check for and kill any process whose command line contains the task's project
   name prefix before starting another.
