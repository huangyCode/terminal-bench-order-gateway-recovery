import argparse
import json
import os
import sys

from .core import Gateway


def respond(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--venue-url", default=os.environ.get("VENUE_URL"))
    args = parser.parse_args()
    gateway = Gateway(args.db, args.venue_url)
    try:
        for raw in sys.stdin:
            try:
                command = json.loads(raw)
                op = command.get("op")
                if op == "submit":
                    gateway.submit(command["cl_ord_id"], command["qty"])
                    respond({"ok": True})
                elif op == "outbound":
                    respond({"messages": gateway.outbound()})
                elif op == "receive":
                    gateway.receive(command["message"])
                    respond({"ok": True})
                elif op == "state":
                    respond({"orders": gateway.state()})
                elif op == "sync":
                    respond({"ok": True, "caught_up": gateway.sync()})
                elif op == "stop":
                    respond({"ok": True})
                    break
                else:
                    raise ValueError("unsupported command")
            except Exception as exc:
                respond({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        gateway.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
