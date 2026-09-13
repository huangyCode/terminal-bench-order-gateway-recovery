# Gateway command and message contract

Run the gateway as `python3 -m gateway.service --db <path>`. When a venue is available, pass `--venue-url <url>` or set `VENUE_URL`. It reads one JSON object per line from standard input and writes exactly one JSON response per command to standard output. The database path may already exist after an uncleanly terminated earlier process.

Commands:

- `{"op":"submit","cl_ord_id":<string>,"qty":<positive integer>}` creates or resumes a client order. Repeating a submitted `cl_ord_id` is idempotent. The response is `{"ok":true}`.
- `{"op":"replace","order_id":<string>,"request_id":<string>,"qty":<positive integer>}` durably appends a replacement to that order's request chain. The request ID is supplied by the client and must remain stable through every retry and restart. The new total quantity cannot be below cumulative filled quantity.
- `{"op":"cancel","order_id":<string>,"request_id":<string>}` durably appends a cancellation to that order's request chain. It refers to the most recently desired request, even when earlier requests are still awaiting venue acknowledgement.
- `{"op":"outbound"}` returns `{"messages":[...]}` containing every business message still awaiting an exchange acknowledgement. Calling it repeatedly, including after restart, may retransmit a message but must preserve the complete message. Each message has a positive, durable `seq`; newly submitted orders receive consecutive outbound sequence numbers beginning at 1.
- `{"op":"receive","message":<message>}` accepts an exchange application message and returns `{"ok":true}`. Messages with a sequence number above the next expected number must remain unapplied until every preceding sequence number has arrived. A duplicate sequence number or `exec_id` has no additional business effect.
- `{"op":"state"}` returns `{"orders":[...]}`. Orders are sorted by client order ID and have exactly `cl_ord_id`, `qty`, `cum_qty`, `leaves_qty`, and `status`.
- `{"op":"sync"}` reconciles durable local state with the configured venue and transmits pending requests in client-sequence order. It returns `{"ok":true,"caught_up":<boolean>}`. `caught_up=false` is a normal retryable outcome: the caller may issue `sync` again, including after restarting the gateway. A response lost after the venue commits must never cause a second business effect.
- `{"op":"stop"}` returns `{"ok":true}` and exits.

Outbound New Order messages contain exactly `seq`, `msg_type="NEW"`, `cl_ord_id`, and `qty`.

Inbound execution messages contain:

- `seq`: positive session sequence number.
- `msg_type`: `ACK`, `FILL`, or `CANCELLED`.
- `exec_id`: stable execution-message identity.
- `cl_ord_id`: the client order identity from the outbound message.
- `last_qty`: non-negative integer; required for `FILL`, otherwise zero.

`ACK` marks the matching outbound order acknowledged and changes `PENDING_NEW` to `NEW`. A `FILL` also acknowledges the matching outbound order, adds `last_qty` exactly once, and changes status to `PARTIALLY_FILLED` or `FILLED`. `CANCELLED` also acknowledges the matching outbound order and changes an unfilled or partially filled order to `CANCELLED`, retaining its cumulative quantity. A terminal order remains terminal. Filling beyond the order quantity, referring to an unknown order, or supplying malformed fields is invalid: the command must return `ok=false`, and no portion of that message—including inbox, execution-deduplication, sequence, order, or acknowledgement state—may be committed. The same sequence number may then be retried with a corrected message.

For an inbound message whose sequence is lower than the next expected sequence, return success without applying a business effect. For a message above the next expected sequence, durably buffer it and return success. When the missing sequence arrives, apply it and then all consecutively buffered messages as one ordered progression. Buffered messages and the expected sequence must survive abrupt process termination. Every successfully consumed inbound sequence number advances durable session state even when its `exec_id` is a business duplicate.

The venue exposes `GET /session`, `POST /request`, `POST /requests`, and `POST /recover`. Session responses contain the venue's durable `next_client_seq` and its ordered response history. Requests contain `client_seq`, stable `request_id`, `type`, `order_id`, `previous_request_id`, `qty`, and `poss_dup`. For an initial order, `type` is `NEW`, `request_id` and `order_id` are the client order ID, `previous_request_id` is null, and `qty` is the submitted quantity. A REPLACE or CANCEL points `previous_request_id` to the preceding request in the order chain; CANCEL sends quantity zero. Reconciliation must treat both the local database and venue session history as authoritative evidence; it must not infer failure merely because an HTTP response was absent.

`POST /requests` transmits an ordered batch as `{"requests":[<request>, ...]}`. A batch carries at least one and
at most 50 requests, in ascending `client_seq` order with no gaps. The venue applies them in array order and
commits each accepted request durably before applying the next. On success it answers `200` with
`{"responses":[...],"accepted":<count>}`, one response per request in the same order. If a request is invalid or
out of sequence the venue stops there and answers `409` with the responses for the durable prefix, that prefix's
`accepted` count, and its current `next_client_seq`; the prefix remains durable. A batch carrying more than 50
requests, or a malformed body, is rejected with `422` and no effect. The connection may also close part-way
through a batch with no response at all: an unknown-length prefix is then durable, and only `GET /session` is
authoritative about how much. A request that the venue read from a batch but did not commit must set
`poss_dup=true` when it is transmitted again.

Reconciliation must be economical with the venue session. Bringing a backlog of `N` pending requests up to date
must not use more than `ceil(N / 50) + 2` transmission calls, counting every `POST /request` and every
`POST /requests` as one call.

Before each first network attempt, the gateway must durably record that the request may have been observed. Every later normal retry uses the complete original request and sets `poss_dup=true`; first attempts use `poss_dup=false`. This attempt state must survive a gateway restart even when the venue disconnected before committing a business effect.

After losing volatile session state, the venue may include `resend_from` in `GET /session`. Before sending any new request, the gateway must account for every original client sequence in `[resend_from,next_client_seq)`, in order, through `POST /recover`. For a request whose acceptance is durably known locally, send `{"action":"GAP_FILL","client_seq":<original sequence>}`. Otherwise send `{"action":"REPLAY","request":<complete original request>}` with the original identity and sequence and `poss_dup=true`, then durably apply the returned response. Recovery is complete only after the entire range is accounted for. A replayed business request must never create a second venue effect.

Venue responses form an independent durable sequence ending just before `next_venue_seq`. The response list may omit a temporarily unavailable sequence while including later responses. The gateway must durably buffer those future responses and report `caught_up=false` until the entire prefix is available. A venue may redeliver an earlier business response at a new `venue_seq`: every delivery sequence must be consumed exactly once, while the stable `exec_id` ensures its request acknowledgement or business transition is applied at most once. Both the buffered gap and execution deduplication must survive restart.

More than one gateway process may be started with the same database path. Concurrent commands across those processes must allocate one gap-free outbound sequence, preserve every accepted client intent, tolerate transient SQLite contention, and converge on the same venue and order state. Concurrent synchronization must not create duplicate business requests. If one worker is killed, another worker using the same database must be able to finish recovery.

The active network reconciler can die after an independent venue commit but before receiving the response. A different process must still be able to append durable intents while the first process waits on network I/O, and after takeover it must finish any requested recovery of the ambiguous prefix before sending that newly appended suffix.
