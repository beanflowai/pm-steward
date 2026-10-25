#!/usr/bin/env bash
# Dispatch one task to the worker: render the wrapper, record the task,
# create the completion hook, ship the files, launch detached.
#
# The dispatch step does not create the hook itself in every host; if
# PM_HOOK_CREATE_CMD is set it is executed here, before the launch (R27).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=pm-config.sh
. "$SCRIPT_DIR/pm-config.sh"

usage() {
  cat <<'EOF'
Usage: dispatch.sh --task-id ID --brief FILE --workdir ABS_PATH [options]

Options:
  --branch NAME     record the branch under test
  --profile NAME    record the runner profile
  --model NAME      record the model
  --origin CHAT     conversation that will receive the wake
  -h, --help        show this help

Environment:
  PM_CHECK=1        dry run: print the plan and exit without connecting
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

TASK_ID=""
BRIEF=""
WORKDIR=""
BRANCH=""
PROFILE=""
MODEL=""
ORIGIN=""

while [ $# -gt 0 ]; do
  case "$1" in
    --task-id|--brief|--workdir|--branch|--profile|--model|--origin)
      [ $# -ge 2 ] || die "$1 needs a value"
      case "$1" in
        --task-id) TASK_ID="$2" ;;
        --brief) BRIEF="$2" ;;
        --workdir) WORKDIR="$2" ;;
        --branch) BRANCH="$2" ;;
        --profile) PROFILE="$2" ;;
        --model) MODEL="$2" ;;
        --origin) ORIGIN="$2" ;;
      esac
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" ;;
  esac
done

[ -n "$TASK_ID" ] || die "--task-id is required"
[ -n "$BRIEF" ] || die "--brief is required"
[ -n "$WORKDIR" ] || die "--workdir is required"

pm_load_config "$SCRIPT_DIR/.." \
  || die "no configuration found; set PM_CONFIG or create config/pm.env"
pm_require PM_WORKER_SSH_TARGET PM_WORKER_SPOOL_DIR PM_WORKER_LOG_DIR \
  PM_WORKER_WRAPPER_DIR PM_RUNNER_CMD PM_REGISTRY_DIR PM_TASK_DIR

pm_safe_id "$TASK_ID" || die "task id must be lowercase kebab-case, at most 64 characters"
pm_safe_path "$WORKDIR" || die "workdir must be an absolute path without quotes or \$"
pm_safe_path "$PM_WORKER_SPOOL_DIR" || die "PM_WORKER_SPOOL_DIR is not a safe absolute path"
pm_safe_path "$PM_WORKER_LOG_DIR" || die "PM_WORKER_LOG_DIR is not a safe absolute path"
pm_safe_path "$PM_WORKER_WRAPPER_DIR" || die "PM_WORKER_WRAPPER_DIR is not a safe absolute path"
[ -f "$BRIEF" ] || die "brief not found: $BRIEF"
case "$PM_RUNNER_CMD" in
  ''|*$'\n'*|*';'*|*'|'*|*'&'*|*'$'*|*'`'*|*'>'*|*'<'*|*'*'*|*'?'*|*'['*|*']'*|*'('*|*')'*|*'{'*|*'}'*|*'"'*|*"'"*|*'\'*)
    die "PM_RUNNER_CMD must be a simple command: no shell metacharacters" ;;
esac

TEMPLATE="${PM_TEMPLATE_PATH:-$SCRIPT_DIR/worker-wrapper.sh.template}"
[ -f "$TEMPLATE" ] || die "wrapper template not found: $TEMPLATE"

LOG_FILE="${PM_WORKER_LOG_DIR%/}/${TASK_ID}.log"
REMOTE_WRAPPER="${PM_WORKER_WRAPPER_DIR%/}/${TASK_ID}.sh"
REMOTE_BRIEF="${PM_WORKER_WRAPPER_DIR%/}/${TASK_ID}.brief.md"
REGISTRY_FILE="${PM_REGISTRY_DIR%/}/${TASK_ID}.json"
TASK_DIR="${PM_TASK_DIR%/}/${TASK_ID}"
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

[ -e "$REGISTRY_FILE" ] && die "task id already used: $TASK_ID (R25); choose a new id"

REMOTE_NETRC=""
if [ "${PM_CHECK:-0}" != "1" ] && [ -n "${PM_NOTIFY_NETRC:-}" ]; then
  [ -f "$PM_NOTIFY_NETRC" ] || die "PM_NOTIFY_NETRC not found: $PM_NOTIFY_NETRC"
  REMOTE_NETRC="${PM_WORKER_WRAPPER_DIR%/}/.${TASK_ID}.netrc"
fi

if [ "${PM_CHECK:-0}" = "1" ]; then
  cat <<EOF
dispatch plan (dry run)
  task id       : $TASK_ID
  worker        : $PM_WORKER_SSH_TARGET
  workdir       : $WORKDIR
  branch        : ${BRANCH:-<not recorded>}
  profile       : ${PROFILE:-<not recorded>}
  model         : ${MODEL:-<not recorded>}
  origin        : ${ORIGIN:-<not recorded>}
  runner        : $PM_RUNNER_CMD
  template      : $TEMPLATE
  remote wrapper: $REMOTE_WRAPPER
  remote brief  : $REMOTE_BRIEF
  log           : $LOG_FILE
  spool         : $PM_WORKER_SPOOL_DIR
  registry      : $REGISTRY_FILE
  hook command  : ${PM_HOOK_CREATE_CMD:-<none>}
  credentials   : ${PM_NOTIFY_NETRC:-<none>}
No files written, no connection made.
EOF
  exit 0
fi

mkdir -p "$PM_REGISTRY_DIR" "$TASK_DIR"
if ! [ "$BRIEF" -ef "$TASK_DIR/brief.md" ]; then
  cp "$BRIEF" "$TASK_DIR/brief.md"
fi

RENDERED=$(mktemp "${TMPDIR:-/tmp}/pm-wrapper.XXXXXX")
cleanup() { rm -f "$RENDERED"; }
trap cleanup EXIT

env \
  TASK_ID="$TASK_ID" \
  BRIEF_FILE="$REMOTE_BRIEF" \
  WORKDIR="$WORKDIR" \
  LOG_FILE="$LOG_FILE" \
  SPOOL_DIR="$PM_WORKER_SPOOL_DIR" \
  PATH_PREFIX="${PM_WORKER_PATH:-}" \
  NOTIFY_URL="${PM_NOTIFY_URL:-}" \
  NOTIFY_TOPIC="${PM_NOTIFY_TOPIC:-}" \
  NOTIFY_NETRC="$REMOTE_NETRC" \
  MONITOR_INTERVAL_SECS="${PM_MONITOR_INTERVAL_SECS:-600}" \
  MONITOR_TICK_SECS="${PM_MONITOR_TICK_SECS:-10}" \
  RUNNER_CMD="$PM_RUNNER_CMD" \
  python3 "$SCRIPT_DIR/render.py" \
    --template "$TEMPLATE" \
    --output "$RENDERED" \
    --allow-empty PATH_PREFIX,NOTIFY_URL,NOTIFY_TOPIC,NOTIFY_NETRC \
  || die "template rendering failed"

write_registry() {
  local pid="${1:-}"
  PMR_PATH="$REGISTRY_FILE" \
  PMR_TASK="$TASK_ID" \
  PMR_HOST="$PM_WORKER_SSH_TARGET" \
  PMR_WORKDIR="$WORKDIR" \
  PMR_LOG="$LOG_FILE" \
  PMR_WRAPPER="$REMOTE_WRAPPER" \
  PMR_BRIEF="$REMOTE_BRIEF" \
  PMR_BRANCH="$BRANCH" \
  PMR_PROFILE="$PROFILE" \
  PMR_MODEL="$MODEL" \
  PMR_ORIGIN="$ORIGIN" \
  PMR_STARTED="$STARTED_AT" \
  PMR_PID="$pid" \
  python3 - <<'PY'
import json, os, tempfile

keys = {
    "task_id": "PMR_TASK",
    "host": "PMR_HOST",
    "workdir": "PMR_WORKDIR",
    "log": "PMR_LOG",
    "wrapper": "PMR_WRAPPER",
    "brief": "PMR_BRIEF",
    "branch": "PMR_BRANCH",
    "profile": "PMR_PROFILE",
    "model": "PMR_MODEL",
    "origin_chat_id": "PMR_ORIGIN",
    "started_at": "PMR_STARTED",
}
record = {name: os.environ.get(env, "") for name, env in keys.items()}
record = {name: value for name, value in record.items() if value}
if os.environ.get("PMR_PID"):
    record["pid"] = int(os.environ["PMR_PID"])

path = os.environ["PMR_PATH"]
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".registry.")
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(record, handle, ensure_ascii=False)
os.replace(tmp, path)
PY
}

if [ -n "${PM_HOOK_CREATE_CMD:-}" ]; then
  [ -x "$PM_HOOK_CREATE_CMD" ] || die "PM_HOOK_CREATE_CMD is not executable"
  "$PM_HOOK_CREATE_CMD" "$TASK_ID" "$ORIGIN" || die "completion hook creation failed"
fi

# Record the task before launching: a launch whose registry write failed would
# be an orphan no sweep could find.
write_registry "" || die "cannot write the dispatch registry"

ssh_run() {
  # PM_SSH_OPTS is intentionally word-split: it carries -o options from config.
  # shellcheck disable=SC2086
  ssh ${PM_SSH_OPTS:-} "$PM_WORKER_SSH_TARGET" "$@"
}

ssh_run "umask 077; mkdir -p '$PM_WORKER_WRAPPER_DIR' '$PM_WORKER_LOG_DIR' '$PM_WORKER_SPOOL_DIR'" \
  || die "cannot prepare worker directories"

if [ -n "$REMOTE_NETRC" ]; then
  ssh_run "umask 077; cat > '$REMOTE_NETRC'" <"$PM_NOTIFY_NETRC" \
    || die "cannot ship the completion credentials"
fi

ssh_run "cat > '$REMOTE_WRAPPER'" <"$RENDERED" || die "cannot ship the wrapper"
ssh_run "cat > '$REMOTE_BRIEF'" <"$BRIEF" || die "cannot ship the brief"

PID=$(ssh_run "cd '$WORKDIR' && nohup bash '$REMOTE_WRAPPER' </dev/null >/dev/null 2>&1 & echo \$!") \
  || die "launch failed"
case "$PID" in
  ''|*[!0-9]*) die "launch returned no pid: $PID" ;;
esac

write_registry "$PID" || die "cannot update the dispatch registry"

printf 'dispatched %s to %s (pid %s)\nlog: %s\nregistry: %s\n' \
  "$TASK_ID" "$PM_WORKER_SSH_TARGET" "$PID" "$LOG_FILE" "$REGISTRY_FILE"
