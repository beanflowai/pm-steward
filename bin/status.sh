#!/usr/bin/env bash
# Read-only task delivery status.
#
# Loads the instance config, passes only status-related variables through a
# scrubbed environment, and runs pm_status.py. It never writes state and never
# opens an SSH or network connection.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

if [ ! -r "$SCRIPT_DIR/pm-config.sh" ]; then
  echo "ERROR: pm-config.sh not found or unreadable: $SCRIPT_DIR/pm-config.sh" >&2
  exit 2
fi

# shellcheck source=pm-config.sh
. "$SCRIPT_DIR/pm-config.sh"

if ! pm_load_config "$SCRIPT_DIR/.."; then
  echo "ERROR: no pm.env found; set PM_CONFIG to the instance config" >&2
  exit 2
fi

: "${PM_STATE_DIR:=}"
: "${PM_REGISTRY_DIR:=}"

if [ -z "$PM_STATE_DIR" ] || [ -z "$PM_REGISTRY_DIR" ]; then
  echo "ERROR: PM_STATE_DIR and PM_REGISTRY_DIR must be non-empty" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found on PATH" >&2
  exit 2
fi

exec env -i \
  PATH="$PATH" LANG="${LANG:-C}" TZ=UTC PYTHONIOENCODING=utf-8 \
  PM_STATE_DIR="$PM_STATE_DIR" \
  PM_REGISTRY_DIR="$PM_REGISTRY_DIR" \
  PM_SENT_LEDGER="${PM_SENT_LEDGER:-$PM_STATE_DIR/handoff-sent.jsonl}" \
  PM_RECEIPTS="${PM_RECEIPTS:-$PM_STATE_DIR/handoff-received.jsonl}" \
  PM_WORKER_SPOOL_DIR="${PM_WORKER_SPOOL_DIR:-}" \
  PM_STATUS_WINDOW_DAYS="${PM_STATUS_WINDOW_DAYS:-7}" \
  PM_STATUS_DONE_OVERDUE_SECS="${PM_STATUS_DONE_OVERDUE_SECS:-3600}" \
  PM_STATUS_DONE_LOST_SECS="${PM_STATUS_DONE_LOST_SECS:-7200}" \
  PM_STATUS_STALE_SECS="${PM_STATUS_STALE_SECS:-7200}" \
  PM_STATUS_TRUSTED_SOURCES="${PM_STATUS_TRUSTED_SOURCES:-pm,PM,watchdog}" \
  PM_STATUS_NOW="${PM_STATUS_NOW:-}" \
  python3 -B "$SCRIPT_DIR/pm_status.py" "$@"
