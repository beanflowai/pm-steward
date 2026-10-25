#!/usr/bin/env bash
# Shared configuration loader for dispatch, sweep, and the smoke test.
# shellcheck shell=bash

pm_repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

# Order: $PM_CONFIG > $XDG_CONFIG_HOME/pm/pm.env > <repo>/config/pm.env
pm_load_config() {
  local repo_dir="${1:-$(pm_repo_root)}" cfg
  for cfg in "${PM_CONFIG:-}" "${XDG_CONFIG_HOME:-$HOME/.config}/pm/pm.env" "$repo_dir/config/pm.env"; do
    if [ -n "$cfg" ] && [ -f "$cfg" ]; then
      # shellcheck disable=SC1090
      . "$cfg"
      PM_CONFIG="$cfg"
      export PM_CONFIG
      return 0
    fi
  done
  return 1
}

pm_require() {
  local missing=() v
  for v in "$@"; do
    [ -n "${!v:-}" ] || missing+=("$v")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    printf 'ERROR: missing configuration: %s\n' "${missing[*]}" >&2
    return 2
  fi
  return 0
}

# Lowercase kebab-case, at most 64 characters, never starts with a dash.
pm_safe_id() {
  local id="$1"
  [ -n "$id" ] || return 1
  [ "${#id}" -le 64 ] || return 1
  case "$id" in
    -*|*[!a-z0-9-]*) return 1 ;;
  esac
  return 0
}

# Absolute, and free of characters that break remote quoting.
pm_safe_path() {
  local p="$1"
  [ -n "$p" ] || return 1
  case "$p" in
    /*) ;;
    *) return 1 ;;
  esac
  case "$p" in
    *"'"*|*'"'*|*'$'*|*'`'*|*$'\n'*) return 1 ;;
  esac
  return 0
}
