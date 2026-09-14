# Metering interface

The metering engine that produced these charges has been decommissioned and its source is gone. What
survives is `/app/samples/trace.jsonl`, a recording of production traffic: a `{"stream":<int>}` marker
opens each stream, and every following line is `{"in":<input>,"out":<output>}` for one event, in the
order the engine saw it. The engine kept state across the events of a stream and started fresh for each
new stream.

## Input line

```
{"seq":<int>,"ts":<int>,"account":<string>,"tier":<string>,"units":<int>,"flag":<int>}
```

- `seq` is a positive integer, strictly increasing across a stream, and may skip values.
- `ts` is Unix seconds, non-decreasing across a stream.
- `account` is 1 to 32 characters from `[A-Za-z0-9_-]`.
- `tier` is one of `a`, `b`, `c`.
- `units` is an integer in `[0, 5000]`.
- `flag` is `0` or `1`.

## Output line

```
{"seq":<int>,"account":<string>,"charge":<int>,"window_units":<int>,"cumulative":<int>}
```

All four numeric fields are integers. `charge` is in cents.

## Replacement

The recording is the only surviving description of the engine's behaviour.

`/app/replica/engine.py` must expose:

```python
class Engine:
    def __init__(self) -> None: ...
    def feed(self, event: dict) -> dict: ...
```

`feed` receives one parsed input line and returns the object the engine writes for it. One `Engine`
instance handles one stream, receiving its events in input order.
