import json
import sqlite3


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS orders(
              cl_ord_id TEXT PRIMARY KEY,
              qty INTEGER NOT NULL,
              cum_qty INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbound(
              cl_ord_id TEXT PRIMARY KEY,
              seq INTEGER NOT NULL UNIQUE,
              payload TEXT NOT NULL,
              acknowledged INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS inbox(
              seq INTEGER PRIMARY KEY,
              payload TEXT NOT NULL,
              applied INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS executions(exec_id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS requests(
              request_id TEXT PRIMARY KEY,
              order_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              previous_request_id TEXT,
              qty INTEGER NOT NULL,
              seq INTEGER NOT NULL UNIQUE,
              acknowledged INTEGER NOT NULL DEFAULT 0,
              send_attempted INTEGER NOT NULL DEFAULT 0
            );
            INSERT OR IGNORE INTO meta(key, value) VALUES ('next_in_seq', 1);
            INSERT OR IGNORE INTO meta(key, value) VALUES ('next_out_seq', 1);
            """
        )
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(orders)")}
        if "current_request_id" not in columns:
            self.db.execute("ALTER TABLE orders ADD COLUMN current_request_id TEXT")
        if "desired_request_id" not in columns:
            self.db.execute("ALTER TABLE orders ADD COLUMN desired_request_id TEXT")
        request_columns = {row[1] for row in self.db.execute("PRAGMA table_info(requests)")}
        if "send_attempted" not in request_columns:
            self.db.execute(
                "ALTER TABLE requests ADD COLUMN send_attempted INTEGER NOT NULL DEFAULT 0"
            )
        self.db.commit()

    def next_in_seq(self) -> int:
        row = self.db.execute("SELECT value FROM meta WHERE key='next_in_seq'").fetchone()
        return int(row[0])

    def set_next_in_seq(self, value: int) -> None:
        self.db.execute("UPDATE meta SET value=? WHERE key='next_in_seq'", (value,))

    def next_out_seq(self) -> int:
        row = self.db.execute("SELECT value FROM meta WHERE key='next_out_seq'").fetchone()
        return int(row[0])

    def set_next_out_seq(self, value: int) -> None:
        self.db.execute("UPDATE meta SET value=? WHERE key='next_out_seq'", (value,))

    def close(self) -> None:
        self.db.close()


def encode(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
