#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/pansou-bangwo
OUT="$(python3 scripts/pansou-watchdog.py 2>&1)" || {
  printf '%s\n' "$OUT"
  exit 1
}
# Stay silent when everything is already healthy. Cron/Hermes only reports real action.
if printf '%s\n' "$OUT" | grep -Eqi 'updating|restored|ERROR'; then
  printf '%s\n' "$OUT"
fi
