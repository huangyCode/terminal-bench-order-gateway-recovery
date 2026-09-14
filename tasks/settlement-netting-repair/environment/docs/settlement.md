# Settlement contract

The pipeline consumes a day's batches and produces one settlement report.

## Batch

A batch is a JSON object with `entries` and `reversals`.

An entry is one side of a posting:

```
{"txn_id":<string>,"seq":<int>,"account":<string>,"counterparty":<string>,
 "currency":<string>,"amount":<positive int>,"side":"debit"|"credit",
 "value_date":<string>,"product":<string>}
```

`seq` is unique and strictly increasing across the whole day. A debit reduces the account's exposure to
its counterparty and a credit increases it. Every transaction posts both sides.

A reversal cancels every entry of its transaction:

```
{"txn_id":<string>,"seq":<int>,"reason":<string>}
```

A reversal may name a transaction from any earlier batch as well as its own, so nothing can be finalised
until the whole day has been consumed.

## Report

```
{"reporting_currency":"USD",
 "payments":[{"payer":<string>,"payee":<string>,"currency":<string>,
              "amount":<int>,"reporting_amount":<int>}, ...],
 "fee_total":<int>,
 "gross_pairs":<int>,
 "net_obligations":<int>,
 "residual_by_account":{<string>:<int>, ...}}
```

- Exposure is tracked per `(account, counterparty, currency)`.
- A counterparty relationship is one relationship seen from two sides, so netting is bilateral: the two
  directions of a pair collapse into a single obligation.
- Fees follow the traffic that was processed, not what survives netting. A pair is charged under one of
  three schedules, chosen from the pair itself rather than from an entry's `product` field, which does
  not affect settlement: `asia` when the currency is JPY or KRW, otherwise `internal` when either side
  of the pair is an account whose name begins `INT`, otherwise `standard`. The charge is the pair's
  gross exposure at the schedule's basis points, truncated, or the schedule's minimum times the pair's
  live leg count, whichever is larger.
- `fee_total` and `reporting_amount` are in reporting minor units. Rates are quoted in units of 1e-6
  reporting per one minor unit of the quoted currency, and conversion truncates toward zero.
- `payments` is sorted by payer, then payee, then currency. `residual_by_account` is sorted by account
  and may hold negative values.

## Entry point

```python
from settle.pipeline import settle
report = settle(batches, rates, schedules)
```

`batches` is a list of `settle.model.Batch`, `rates` maps currency to integer rate, and `schedules` maps
product name to `settle.model.FeeSchedule`.
