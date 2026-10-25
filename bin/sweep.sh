#!/usr/bin/env bash
# Read-only reconciliation. Compares the registry, the worker event pool, and
# the received receipts, and reports what needs attention. It never writes.
#
# Run it on a schedule as the backstop for a lost wake (R22, R24).

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=pm-config.sh
. "$SCRIPT_DIR/pm-config.sh"

pm_load_config "$SCRIPT_DIR/.." || {
  echo "ERROR: no configuration found" >&2
  exit 2
}
pm_require PM_REGISTRY_DIR PM_WORKER_SSH_TARGET PM_WORKER_SPOOL_DIR || exit 2
pm_safe_path "$PM_WORKER_SPOOL_DIR" || { echo "ERROR: unsafe PM_WORKER_SPOOL_DIR" >&2; exit 2; }

export PM_REGISTRY_DIR PM_WORKER_SSH_TARGET PM_WORKER_SPOOL_DIR
export PM_SWEEP_RECEIVED="${PM_STATE_DIR:-$HOME/.local/state/pm}/handoff-received.jsonl"
export PM_SWEEP_STALE_SECS="${PM_SWEEP_STALE_SECS:-2100}"
export PM_SWEEP_START_GRACE_SECS="${PM_SWEEP_START_GRACE_SECS:-300}"
export PM_SWEEP_LOST_AFTER_SECS="${PM_SWEEP_LOST_AFTER_SECS:-3600}"

python3 - <<'PY'
import datetime
import glob
import json
import os
import subprocess
import sys
import time

registry_dir = os.environ["PM_REGISTRY_DIR"]
host = os.environ["PM_WORKER_SSH_TARGET"]
spool = os.environ["PM_WORKER_SPOOL_DIR"].rstrip("/")
received_path = os.environ["PM_SWEEP_RECEIVED"]
stale = int(os.environ["PM_SWEEP_STALE_SECS"])
grace = int(os.environ["PM_SWEEP_START_GRACE_SECS"])
lost_after = int(os.environ["PM_SWEEP_LOST_AFTER_SECS"])
now = time.time()


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()
    except ValueError:
        return None


def load_received():
    tasks = set()
    try:
        with open(received_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("task_id") and record.get("kind") == "done":
                    tasks.add(record["task_id"])
    except FileNotFoundError:
        pass
    return tasks


def fetch_records(task):
    remote = (
        f"cat '{spool}/{task}.started.json' 2>/dev/null; printf '\\n'; "
        f"cat '{spool}/{task}.done.json' 2>/dev/null"
    )
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        host,
        remote,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return None, None, False
    if result.returncode != 0:
        return None, None, False
    first, _, rest = result.stdout.partition("\n")
    parts = [first.strip(), rest.strip()]
    records = []
    for part in parts:
        if not part:
            records.append(None)
            continue
        try:
            records.append(json.loads(part))
        except json.JSONDecodeError:
            records.append(None)
    return records[0], records[1], True


def age(value):
    ts = parse_ts(value)
    return None if ts is None else int(now - ts)


received = load_received()
entries = sorted(glob.glob(os.path.join(registry_dir, "*.json")))
findings = []

print(f"registry  {registry_dir}")
print(f"worker    {host}:{spool}")
print(f"received  {received_path}")
print()

for path in entries:
    try:
        with open(path, encoding="utf-8") as handle:
            reg = json.load(handle)
    except (OSError, json.JSONDecodeError):
        print(f"BAD      {os.path.basename(path)}  unreadable registry entry")
        findings.append("bad-registry")
        continue

    task = reg.get("task_id") or os.path.basename(path)[:-5]
    started, done, reachable = fetch_records(task)
    task_age = age(reg.get("started_at"))
    started_age = age(started.get("at")) if started else None
    done_age = age(done.get("at")) if done else None

    if not reachable:
        state = "UNREACHABLE"
        detail = "cannot read the event pool; classification skipped"
    elif started is None and done is None and task_age is not None and task_age > grace:
        state = "FAILED_TO_START"
        detail = f"no started record after {task_age}s"
    elif started and not done and started_age is not None and started_age > stale:
        state = "POSSIBLY_HUNG"
        detail = f"no done record {started_age}s after start"
    elif done:
        if task in received:
            state = "OK"
            detail = f"done status={done.get('status')}"
        elif done_age is not None and done_age > lost_after:
            state = "LOST_WAKE"
            detail = f"done exists, no receipt for {done_age}s"
        else:
            state = "UNCLAIMED"
            detail = f"done status={done.get('status')}, no receipt yet"
    else:
        state = "RUNNING"
        detail = f"{task_age}s since dispatch" if task_age is not None else "in flight"

    if state not in ("OK", "RUNNING"):
        findings.append(state)
    print(f"{state:<16} {task:<28} {detail}")

print()
if findings:
    print(f"needs attention: {len(findings)}")
    sys.exit(0)

print("needs attention: 0")
PY
