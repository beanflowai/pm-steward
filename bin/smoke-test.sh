#!/usr/bin/env bash
# Static self-check. Verifies syntax, configuration, rendering, links, and
# that no instance identifier leaked. Pass --live to also touch the worker.
#
# Exit: 0 pass, 1 failure, 2 configuration problem.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
# shellcheck source=pm-config.sh
. "$SCRIPT_DIR/pm-config.sh"

LIVE=0
[ "${1:-}" = "--live" ] && LIVE=1

FAILED=0
ok() { printf 'ok    %s\n' "$*"; }
warn() { printf 'warn  %s\n' "$*"; }
bad() { printf 'FAIL  %s\n' "$*"; FAILED=1; }

echo "== syntax =="
for file in "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.sh.template; do
  [ -f "$file" ] || continue
  if bash -n "$file" 2>/dev/null; then ok "bash $file"; else bad "bash $file"; fi
done
if python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' \
  "$SCRIPT_DIR/render.py" 2>/dev/null; then
  ok "python render.py"
else
  bad "python render.py"
fi

echo "== configuration =="
if pm_load_config "$REPO_ROOT"; then
  ok "config $PM_CONFIG"
else
  bad "no configuration; set PM_CONFIG or create config/pm.env"
  echo
  echo "static checks above may still have value; stopping configuration checks"
  exit 2
fi

if pm_require PM_WORKER_SSH_TARGET PM_WORKER_SPOOL_DIR PM_WORKER_LOG_DIR \
  PM_WORKER_WRAPPER_DIR PM_RUNNER_CMD PM_REGISTRY_DIR PM_TASK_DIR; then
  ok "required variables"
else
  bad "required variables"
  echo
  echo "fix the configuration and re-run"
  exit 2
fi

echo "== rendering =="
RENDER_OUT=$(mktemp "${TMPDIR:-/tmp}/pm-smoke.XXXXXX")
if env \
  TASK_ID="smoke-001" \
  BRIEF_FILE="/tmp/smoke.brief.md" \
  WORKDIR="/tmp/smoke-workdir" \
  LOG_FILE="${PM_WORKER_LOG_DIR%/}/smoke-001.log" \
  SPOOL_DIR="$PM_WORKER_SPOOL_DIR" \
  PATH_PREFIX="${PM_WORKER_PATH:-}" \
  NOTIFY_URL="${PM_NOTIFY_URL:-}" \
  NOTIFY_TOPIC="${PM_NOTIFY_TOPIC:-}" \
  NOTIFY_NETRC="${PM_NOTIFY_NETRC:-}" \
  MONITOR_INTERVAL_SECS="${PM_MONITOR_INTERVAL_SECS:-600}" \
  MONITOR_TICK_SECS="${PM_MONITOR_TICK_SECS:-10}" \
  RUNNER_CMD="$PM_RUNNER_CMD" \
  python3 "$SCRIPT_DIR/render.py" \
    --template "$SCRIPT_DIR/worker-wrapper.sh.template" \
    --output "$RENDER_OUT" \
    --allow-empty PATH_PREFIX,NOTIFY_URL,NOTIFY_TOPIC,NOTIFY_NETRC 2>/dev/null; then
  if grep -q '{{' "$RENDER_OUT"; then
    bad "unresolved placeholder in rendered wrapper"
  else
    ok "wrapper template renders"
  fi
else
  bad "wrapper template rendering failed"
fi
rm -f "$RENDER_OUT"

echo "== portability =="
PORTABLE_BAD=0
for file in "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.sh.template; do
  case "$file" in
    *smoke-test.sh) continue ;;
  esac
  if grep -qE 'find .*-printf|sed -i |stat -c ' "$file" 2>/dev/null; then
    bad "GNU-only flags in $file"
    PORTABLE_BAD=1
  fi
done
[ "$PORTABLE_BAD" -eq 0 ] && ok "no GNU-only find/sed/stat flags"

echo "== leaks =="
LEAK=0
if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  TRACKED=$(git -C "$REPO_ROOT" ls-files)
else
  TRACKED=$(cd "$REPO_ROOT" && find . -type f -not -path './.git/*' | sed 's|^\./||')
fi

matches_re() {
  local pattern="$1" file
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    if grep -qE -- "$pattern" "$REPO_ROOT/$file" 2>/dev/null; then
      return 0
    fi
  done <<<"$TRACKED"
  return 1
}

matches_fixed() {
  local pattern="$1" file
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    if grep -qiF -- "$pattern" "$REPO_ROOT/$file" 2>/dev/null; then
      return 0
    fi
  done <<<"$TRACKED"
  return 1
}

for pattern in 'AIza[0-9A-Za-z_-]{20,}' 'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' 'sheet_id=[A-Za-z0-9_-]{20,}'; do
  if matches_re "$pattern"; then
    bad "secret-like value matches: $pattern"
    LEAK=1
  fi
done
[ "$LEAK" -eq 0 ] && ok "no obvious secrets"

if [ -n "${PM_SMOKE_DENY:-}" ]; then
  IFS=',' read -r -a DENY <<<"$PM_SMOKE_DENY"
  for term in ${DENY[@]+"${DENY[@]}"}; do
    [ -n "$term" ] || continue
    if matches_fixed "$term"; then
      bad "denied identifier present: $term"
      LEAK=1
    fi
  done
  [ "$LEAK" -eq 0 ] && ok "deny list clean"
fi

echo "== language =="
if python3 - "$REPO_ROOT" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
hits = []
for path in root.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        hits.append(str(path.relative_to(root)))
if hits:
    print("CJK characters in: " + ", ".join(hits))
    sys.exit(1)
PY
then
  ok "English only"
else
  bad "non-English characters found"
fi

echo "== links =="
if python3 - "$REPO_ROOT" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
pattern = re.compile(r"\]\(([^)]+)\)")
missing = []
for path in root.rglob("*.md"):
    if ".git" in path.parts:
        continue
    for target in pattern.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if not (path.parent / target).resolve().exists():
            missing.append(f"{path.relative_to(root)} -> {target}")
if missing:
    print("missing links: " + "; ".join(missing))
    sys.exit(1)
PY
then
  ok "internal links resolve"
else
  bad "broken internal links"
fi

if [ "$LIVE" -eq 1 ]; then
  echo "== live =="
  runner="${PM_RUNNER_CMD%% *}"
  if ssh ${PM_SSH_OPTS:-} -o BatchMode=yes -o ConnectTimeout=10 "$PM_WORKER_SSH_TARGET" \
    "export PATH='${PM_WORKER_PATH:-.}':\$PATH; command -v '$runner'"; then
    ok "worker reachable and runner found"
  else
    bad "worker unreachable or runner missing"
  fi
  if [ -n "${PM_NOTIFY_URL:-}" ] && [ -n "${PM_NOTIFY_TOPIC:-}" ]; then
    if [ -f "${PM_NOTIFY_NETRC:-/nonexistent}" ]; then
      code=$(curl -sS -o /dev/null -m 10 -w '%{http_code}' --netrc-file "$PM_NOTIFY_NETRC" \
        -d "smoke $(date +%s)" "$PM_NOTIFY_URL/$PM_NOTIFY_TOPIC" 2>/dev/null || echo 000)
      case "$code" in
        2*) ok "completion channel accepts a publish ($code)" ;;
        *) bad "completion channel publish failed ($code)" ;;
      esac
    else
      bad "PM_NOTIFY_NETRC missing; cannot verify the completion channel"
    fi
  fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "PASS"
  exit 0
fi
echo "FAIL"
exit 1
