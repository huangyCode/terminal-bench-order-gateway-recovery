# Terminal-Bench task candidates v1

Date: 2026-09-13
Status: provisional; domain assumption is financial-data/backend infrastructure.

## Selection principles

Each candidate is evaluated against the frozen upstream proposal rubric: verifiable, well-specified, solvable by an expert in a few hours once the approach is known, difficult for a meaningful reason, realistic/valuable, outcome-verified, novel, and agentic. Candidates must also be feasible to implement and harden within the interview window.

Scores use a 1–5 scale. Higher delivery-risk scores mean safer/easier to deliver.

## Candidate A: Crash-safe FIX order gateway recovery

### Real-world scenario

A trading venue gateway has an incomplete FIX-like session/order-state implementation. During disconnects and process restarts it can duplicate orders, lose execution reports, mishandle sequence gaps, or expose an incorrect order state. Repair the gateway so that it maintains exactly-once business effects and correct session recovery while a verifier-controlled exchange introduces deterministic disconnects, delayed/duplicated messages, resend requests, gap fills, and crash points.

### Agent outcome

The agent repairs the application under `/app`. The final service must interoperate with the documented protocol and pass verifier-driven black-box scenarios. The verifier grades externally observable order/execution state and protocol behavior, not source-code structure.

### Natural difficulty

- Coordinating protocol sequence state with durable business state.
- Distinguishing transport duplication from business duplication.
- Handling resend/gap-fill semantics across crashes.
- Preserving exactly-once order effects when acknowledgements and execution reports cross reconnect boundaries.
- Debugging a stateful system through iterative runs rather than implementing a standalone function.

### Verification design

A separate verifier container owns the exchange simulator and deterministic scenario seeds. It launches the submitted gateway unprivileged, injects faults at controlled protocol boundaries, and checks exchange-side accepted orders plus client-visible final states. Public smoke scenarios allow iteration; hidden scenarios vary IDs, timings, restart points, duplication, and gap patterns without introducing new protocol rules.

### Anti-cheat properties

The agent cannot see hidden scenarios or ground truth. Passing requires interoperating with the verifier service. Scenario values are varied, so fixed outputs cannot pass. The verifier reward channel remains outside the process executing agent code.

### Main risks

- Multi-container integration and deterministic fault scheduling may consume substantial implementation time.
- The instruction must specify protocol semantics sufficiently without becoming a catalogue of arbitrary edge cases.
- Timing-sensitive tests must be designed as event-driven state machines, not flaky sleeps.

## Candidate B: Exchange event-ledger reconciliation with busts and corrections

### Real-world scenario

A trade-capture service must reconstruct canonical fills, cash movements, positions, realized PnL, and fees from multiple venue streams containing out-of-order delivery, duplicates, trade corrections, busts, session resets, and venue-specific identifiers. The existing implementation is stale and produces inconsistent books. Repair it so it works on same-schema unseen reconciliation packets.

### Agent outcome

The agent repairs a CLI/library. Given a packet directory, it produces a canonical SQLite ledger and reconciliation report. It must support verifier-provided packets governed by the same documented event vocabulary and accounting rules.

### Natural difficulty

- Event identity differs from economic identity.
- Corrections and busts form causal chains that may arrive out of order.
- Position, fee, and cash invariants must remain mutually consistent.
- Replay must be deterministic and idempotent.
- Several plausible local fixes fail global accounting invariants.

### Verification design

The verifier generates deterministic hidden packets and compares normalized outcomes and accounting invariants against an independent reference implementation. It checks idempotent replay, permutation invariance where allowed, causal resolution, and conservation constraints. It does not require the candidate to match the Oracle's internal schema beyond the documented output contract.

### Anti-cheat properties

Hidden packets vary event values and order. The verifier independently recomputes expected results. Static output, input-specific hash maps, or copying sample results will fail.

### Main risks

- Potential conceptual overlap with `risk-scorer-replay` because both repair an offline evaluator for unseen packets.
- Excessive accounting cases could become overspecification rather than essential difficulty.
- A strong model may implement the state machine successfully if the vocabulary remains small.

## Candidate C: Point-in-time market-data lake repair

### Real-world scenario

A partitioned Parquet market-data lake contains late trades, duplicate vendor revisions, symbol remaps, timezone/calendar errors, and partially published partitions. Repair the incremental build pipeline so every as-of query produces a consistent historical view, repeat runs are idempotent, and a failed publish cannot expose a mixed snapshot.

### Agent outcome

The agent repairs a local data pipeline and publication protocol. The verifier supplies unseen same-schema raw batches, interrupts selected phases, retries builds, and validates point-in-time query results and atomic publication behavior.

### Natural difficulty

- Bitemporal event time versus vendor revision/arrival time.
- Deterministic deduplication and symbol-history joins.
- Calendar/session boundaries around timezone transitions.
- Crash-safe atomic publication and idempotent retries.
- Correctness must hold across full and incremental rebuilds.

### Verification design

An independent reference builds expected logical tables for deterministic hidden datasets. Tests compare query outcomes after full builds, incremental builds, and injected crash/retry schedules. Filesystem publication is checked for atomic snapshots and absence of mixed-version reads.

### Anti-cheat properties

Hidden data changes values, partitions, revision order, calendars, and interruption points. Functional queries and crash/retry behavior are exercised; file names or fixed rows are insufficient.

### Main risks

- Potential overlap with general ETL/data-engineering benchmark tasks.
- Timezone/calendar cases can look like arbitrary corner-case accumulation.
- Atomic-reader verification needs careful isolation to avoid timing flakiness.

## Comparative scoring

| Criterion | Weight | A: FIX gateway | B: Event ledger | C: Data lake |
|---|---:|---:|---:|---:|
| Real-world value | 20% | 5 | 5 | 5 |
| Essential difficulty | 20% | 5 | 4 | 4 |
| Objective verification | 20% | 5 | 5 | 4 |
| Agentic/long-horizon quality | 15% | 5 | 4 | 4 |
| Anti-cheat robustness | 10% | 5 | 5 | 5 |
| Novelty vs current 66 tasks | 5% | 5 | 3 | 4 |
| Delivery safety within interview window | 10% | 3 | 5 | 4 |
| Weighted score / 5 | 100% | 4.70 | 4.35 | 4.20 |

## Provisional recommendation

Candidate A, crash-safe FIX order gateway recovery, is the strongest benchmark concept. It has the clearest real-world value, naturally stateful multi-step difficulty, strong black-box verification, and little direct overlap with the 66 task folders at the frozen upstream revision. Its main weakness is implementation risk, so it should proceed only if a one-day vertical prototype can demonstrate deterministic fault injection, Oracle success, and stable verifier isolation.

Candidate B is the fallback if Candidate A's multi-container prototype is not stable within one day. It is faster to implement and easier to verify, but must be differentiated carefully from the existing `risk-scorer-replay` task and must avoid turning into a long list of accounting cases.

## Prototype go/no-go gate for Candidate A

Proceed only if all are true:

1. A minimal gateway and verifier-controlled exchange can complete a normal session deterministically.
2. The verifier can force a disconnect at a named protocol boundary without wall-clock race assumptions.
3. The Oracle survives one reconnect/resend case and one crash/restart case.
4. The verifier can distinguish duplicate business effects from duplicate transport messages.
5. Hidden scenario inputs can vary without adding rules absent from the instruction/protocol document.
6. The entire smoke suite completes comfortably inside the proposed verifier timeout.

If any condition fails within the prototype budget, switch to Candidate B rather than weakening determinism or verifier quality.

