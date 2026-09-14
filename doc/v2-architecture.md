# Order gateway recovery v2 architecture

Status: implementation design after development trial D1 showed the synchronous prototype was functionally solved by Codex.

## Objective

Turn the validated process-isolated prototype into a realistic distributed recovery task. The hard part is one coherent problem: keeping client intent, durable gateway state, venue-observed effects, and two sequence spaces consistent when either side can lose a response or restart.

## Components

### Agent-owned gateway

The artifact remains `/app/gateway`. A supervisor process exposes the existing JSON-lines operator interface and communicates with a venue over a documented TCP JSON-lines protocol. The Agent may replace the implementation but must preserve both interfaces.

### Public venue

The development environment includes a venue sidecar with visible documentation and smoke scenarios. It supports normal traffic and a small set of user-selectable faults so the Agent can reproduce incidents.

### Verifier venue

The separate verifier contains its own peer following the same protocol, baked into the verifier image and unreachable from the agent container. It varies values, interleavings, disconnect boundaries, replay windows, and restart points, but introduces no new message type or semantic rule. It owns the authoritative business-effect ledger.

The verifier peer and the development sidecar are deliberately close relatives rather than independent
reimplementations: they must agree on the documented contract exactly, and two separately written peers would
drift and turn protocol ambiguity into unfair failures. The verifier peer carries the fault injection and the
authoritative ledger the sidecar does not, which is where the two diverge (58 differing lines at the current
revision). The isolation that matters is that the agent can neither read the verifier peer nor reach it, not that
it was written twice.

## Business request model

Three request types form an order chain:

- `NEW(request_id, order_id, qty)` creates the root order.
- `REPLACE(request_id, order_id, previous_request_id, qty)` changes remaining quantity while retaining fills. The new total cannot be below cumulative fill.
- `CANCEL(request_id, order_id, previous_request_id)` cancels the current live version.

Every request has a stable `request_id`. Replaying the same request is idempotent. Reusing a request ID with different content is rejected. A replacement or cancellation is valid only when `previous_request_id` identifies the current accepted version of that order.

## Two independent sequence spaces

- `client_seq`: gateway-to-venue session sequence, durable and strictly increasing for first transmissions.
- `venue_seq`: venue-to-gateway session sequence, durable and applied in order.

Business identity is not session identity. A retransmitted request keeps `request_id` and original `client_seq` while setting `poss_dup=true`. Duplicate execution reports may arrive under a new `venue_seq` but retain their stable `exec_id`; the gateway consumes the new session sequence without applying the business effect twice.

## Outbound recovery

The venue may disconnect at any of these boundaries:

1. before reading a request;
2. after durably accepting it but before responding;
3. after sending a response that the gateway has not durably applied.

After reconnect, the venue declares the next `client_seq` it expects. The gateway must:

- transmit unsent messages in order;
- replay requested application messages with original sequence and identity;
- emit gap-fill ranges for sequence slots whose business messages are already known to have been accepted and need not be replayed;
- never create a fresh request ID to resolve ambiguity.

## Inbound recovery

The gateway durably buffers future `venue_seq` messages, requests missing ranges, and applies only the contiguous prefix. Inbox receipt, business transition, execution deduplication, request acknowledgement, and advancement of the expected venue sequence are atomic. Buffered gaps survive abrupt termination.

## Operator commands

The JSON-lines operator interface will support:

- `submit`
- `replace`
- `cancel`
- `sync`
- `state`
- `stop`

`submit`, `replace`, and `cancel` durably record intent before reporting success. `sync` advances network recovery until the gateway is caught up or a documented retryable error occurs. It is safe to call repeatedly and after restart.

## Observable state

Normalized order state contains:

- root order ID;
- current accepted request ID;
- desired request ID;
- total quantity;
- cumulative filled quantity;
- leaves quantity;
- status;
- pending request, if any.

The verifier compares this state with the venue ledger and the submitted client-intent history.

## Deterministic fault model

Faults are event barriers, never wall-clock sleeps:

- disconnect before venue receive;
- disconnect after venue commit/before response;
- disconnect after response write/before gateway commit;
- gateway kill after durable intent;
- gateway kill after send/before inbound commit;
- venue restart retaining its durable ledger;
- duplicate execution under a new venue sequence;
- future venue message delivered before a missing predecessor;
- resend request spanning accepted and pending client sequences.

Each barrier is triggered by a named protocol event. Seeds choose values and schedules, not semantics.

## Verifier gates

All gates are binary:

1. Interface and artifact safety.
2. Stable business identity across ambiguous retries.
3. Ordered outbound recovery and resend/gap-fill behavior.
4. Durable inbound gap recovery.
5. Cross-sequence business deduplication.
6. NEW/REPLACE/CANCEL chain correctness.
7. Transaction rollback for rejected requests/reports.
8. Gateway/venue agreement after each recovery epoch.
9. Deterministic replay from the same initial state and fault schedule.
10. Bounded completion without spin or retry storms.

## Anti-cheat boundary

- Verifier scenarios and authoritative ledger never enter the Agent image.
- The verifier starts Agent code as an unprivileged user.
- `/tests` and `/logs/verifier` are inaccessible to that user.
- Agent code communicates only with the venue address explicitly supplied to it.
- The venue checks semantic protocol behavior; a fabricated final JSON cannot create matching venue effects.
- IDs and schedules vary per hidden deterministic seed.
- Agent artifacts are copied before verifier execution and made read-only.
- Infrastructure setup failures do not write a scoreable zero; after setup succeeds, task failures write binary zero.

## Scope exclusions

- Full FIX encoding/tag grammar.
- TLS and credential management.
- Matching-engine price/time priority.
- Market data, PnL, risk, and latency optimization.
- Real-time randomized sleeps.
- Source-pattern grading.

## Go/no-go for v2

Proceed to formal trials only if:

- independent public and verifier peers agree on the documented protocol;
- Oracle passes repeated fault schedules;
- known broken variants fail for the intended invariant;
- no verifier test relies on undocumented semantics;
- a clean Codex development run fails a functional gate rather than formatting or infrastructure;
- the implementation rubric does not flag overlap, overspecification, process grading, or nondeterminism.

