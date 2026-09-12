#!/usr/bin/env bash
set -euo pipefail
db_path="${1:-/tmp/gateway-smoke.db}"
rm -f "$db_path"
python3 -m gateway.service --db "$db_path" <<'EOF'
{"op":"submit","cl_ord_id":"SMOKE-1","qty":10}
{"op":"outbound"}
{"op":"receive","message":{"seq":1,"msg_type":"ACK","exec_id":"A-1","cl_ord_id":"SMOKE-1","last_qty":0}}
{"op":"receive","message":{"seq":2,"msg_type":"FILL","exec_id":"F-1","cl_ord_id":"SMOKE-1","last_qty":4}}
{"op":"state"}
{"op":"stop"}
EOF

