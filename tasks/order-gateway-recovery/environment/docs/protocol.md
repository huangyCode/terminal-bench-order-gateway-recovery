# Gateway command and message contract

Run the gateway as `python3 -m gateway.service --db <path>`. It reads one JSON object per line from standard input and writes exactly one JSON response per command to standard output. The database path may already exist after an uncleanly terminated earlier process.

Commands:

- `{"op":"submit","cl_ord_id":<string>,"qty":<positive integer>}` creates or resumes a client order. Repeating a submitted `cl_ord_id` is idempotent. The response is `{"ok":true}`.
- `{"op":"outbound"}` returns `{"messages":[...]}` containing every business message still awaiting an exchange acknowledgement. Calling it repeatedly, including after restart, may retransmit a message but must preserve the complete message. Each message has a positive, durable `seq`; newly submitted orders receive consecutive outbound sequence numbers beginning at 1.
- `{"op":"receive","message":<message>}` accepts an exchange application message and returns `{"ok":true}`. Messages with a sequence number above the next expected number must remain unapplied until every preceding sequence number has arrived. A duplicate sequence number or `exec_id` has no additional business effect.
- `{"op":"state"}` returns `{"orders":[...]}`. Orders are sorted by client order ID and have exactly `cl_ord_id`, `qty`, `cum_qty`, `leaves_qty`, and `status`.
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
