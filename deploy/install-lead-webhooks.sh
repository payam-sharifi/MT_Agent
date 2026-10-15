#!/usr/bin/env bash
set -euo pipefail

SRC="${HERMES_HOME:-/root/.hermes}/deploy/webhook_subscriptions.leads.json"
DEST="${HERMES_HOME:-/root/.hermes}/webhook_subscriptions.json"
ENV_FILE="${HERMES_HOME:-/root/.hermes}/.env"

if [[ ! -f "$SRC" ]]; then
  echo "lead webhook routes missing: $SRC"
  exit 0
fi

SECRET=""
if [[ -f "$ENV_FILE" ]]; then
  SECRET="$(python3 - "$ENV_FILE" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
match = re.search(r"(?m)^WEBHOOK_SECRET=(.*)$", text)
print((match.group(1).strip().strip('"').strip("'") if match else ""), end="")
PY
)"
fi

python3 - "$SRC" "$DEST" "$SECRET" <<'PY'
import json, sys
from pathlib import Path

src, dest, secret = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
incoming = json.loads(src.read_text(encoding="utf-8"))
current = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
for name, route in incoming.items():
    if secret and not route.get("secret"):
        route["secret"] = secret
    current[name] = route
dest.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
print(f"installed lead webhook routes: {', '.join(incoming)}")
PY
