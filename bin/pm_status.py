#!/usr/bin/env python3
"""Read-only PM status query.

Reads the local dispatch registry and handoff sent/received ledgers, classifies
each task's delivery lifecycle, and prints a table or JSON. It never writes,
never opens a network connection, and never reads done.json or Goals state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

SCHEMA_VERSION = 1
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
EPOCH_RE = re.compile(r"^\d+(?:\.\d+)?$")
OFFSET_NO_COLON_RE = re.compile(r"^(.*T.*[+-]\d{2})(\d{2})$")
FRACTION_RE = re.compile(r"^(.*\.\d{6})\d+(.*)$")

COUNT_STATES = (
    "unconfirmed",
    "done_sent",
    "done_overdue",
    "done_lost",
    "done_received",
    "failed_recorded",
    "orphan",
    "unknown",
)
STATE_ORDER = {state: index for index, state in enumerate(COUNT_STATES)}
FLAG_ORDER = ("failed_to_start", "possibly_hung", "stale")

SENT_KINDS = {"done", "failed_to_start", "possibly_hung", "check_reminder"}
RECEIVED_KINDS = {"done", "failed", "possibly_hung", "failed_to_start", "check_reminder"}
TERMINAL_RECEIVED_KINDS = {"done", "failed"}

DEFAULT_TRUSTED_SOURCES = ("pm", "PM", "watchdog")
DEFAULT_WINDOW_DAYS = 7
DEFAULT_DONE_OVERDUE_SECS = 3600
DEFAULT_DONE_LOST_SECS = 7200
DEFAULT_STALE_SECS = 7200


class ConfigError(Exception):
    pass


@dataclass
class Warning:
    code: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }


class Warnings:
    def __init__(self) -> None:
        self.items: List[Warning] = []
        self._seen: Set[Tuple[str, Optional[str], Optional[int], str]] = set()

    def add(
        self,
        code: str,
        message: str,
        file: Optional[object] = None,
        line: Optional[int] = None,
    ) -> None:
        file_text = str(file) if file is not None else None
        key = (code, file_text, line, message)
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append(Warning(code, message, file_text, line))


@dataclass
class Event:
    kind: str
    at: datetime
    source: Optional[str]
    line: int


@dataclass
class RegistryRecord:
    task_id: str
    path: str
    corrupt: bool = False
    host: Optional[str] = None
    log: Optional[str] = None
    started_at: Optional[datetime] = None
    mismatch: bool = False


@dataclass
class TaskStatus:
    task_id: str
    state: str
    actionable: bool
    flags: List[str]
    dispatched_at: Optional[datetime]
    age_secs: Optional[int]
    host: Optional[str]
    log: Optional[str]
    sent: List[Event]
    received: List[Event]
    hint: str


@dataclass
class Config:
    state_dir: Path
    registry_dir: Path
    sent_ledger: Path
    received_ledger: Path
    spool_dir: Optional[Path]
    window_days: int
    done_overdue_secs: int
    done_lost_secs: int
    stale_secs: int
    trusted_sources: Set[str]


def parse_ts(value: object) -> Optional[datetime]:
    """Parse ISO8601, naive ISO (UTC), or epoch seconds. Return None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if EPOCH_RE.match(text):
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    normalized = text.replace("Z", "+00:00")
    match = OFFSET_NO_COLON_RE.match(normalized)
    if match:
        normalized = f"{match.group(1)}:{match.group(2)}"
    fraction_match = re.match(
        r"^(.*T\d{2}:\d{2}:\d{2})\.(\d+)(.*)$", normalized
    )
    if fraction_match:
        fraction = (fraction_match.group(2) + "000000")[:6]
        normalized = (
            f"{fraction_match.group(1)}.{fraction}{fraction_match.group(3)}"
        )
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        match = FRACTION_RE.match(normalized)
        if not match:
            return None
        try:
            parsed = datetime.fromisoformat(match.group(1) + match.group(2))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_ts(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a positive integer, got {raw!r}")
    if value < 1:
        raise ConfigError(f"{name} must be a positive integer, got {raw!r}")
    return value


def load_config() -> Config:
    state_raw = os.environ.get("PM_STATE_DIR", "").strip()
    registry_raw = os.environ.get("PM_REGISTRY_DIR", "").strip()
    if not state_raw:
        raise ConfigError("PM_STATE_DIR is empty")
    if not registry_raw:
        raise ConfigError("PM_REGISTRY_DIR is empty")

    trusted_raw = os.environ.get("PM_STATUS_TRUSTED_SOURCES")
    if trusted_raw is None:
        trusted = set(DEFAULT_TRUSTED_SOURCES)
    else:
        trusted = {item.strip() for item in trusted_raw.split(",") if item.strip()}

    spool_raw = os.environ.get("PM_WORKER_SPOOL_DIR", "").strip()
    sent_raw = os.environ.get("PM_SENT_LEDGER", "").strip()
    received_raw = os.environ.get("PM_RECEIPTS", "").strip()
    sent_ledger = Path(sent_raw) if sent_raw else Path(state_raw) / "handoff-sent.jsonl"
    received_ledger = (
        Path(received_raw) if received_raw else Path(state_raw) / "handoff-received.jsonl"
    )
    done_overdue_secs = parse_positive_int_env(
        "PM_STATUS_DONE_OVERDUE_SECS", DEFAULT_DONE_OVERDUE_SECS
    )
    done_lost_secs = parse_positive_int_env(
        "PM_STATUS_DONE_LOST_SECS", DEFAULT_DONE_LOST_SECS
    )
    if done_lost_secs <= done_overdue_secs:
        raise ConfigError(
            "PM_STATUS_DONE_LOST_SECS must be greater than "
            "PM_STATUS_DONE_OVERDUE_SECS"
        )

    return Config(
        state_dir=Path(state_raw),
        registry_dir=Path(registry_raw),
        sent_ledger=sent_ledger,
        received_ledger=received_ledger,
        spool_dir=Path(spool_raw) if spool_raw else None,
        window_days=parse_positive_int_env(
            "PM_STATUS_WINDOW_DAYS", DEFAULT_WINDOW_DAYS
        ),
        done_overdue_secs=done_overdue_secs,
        done_lost_secs=done_lost_secs,
        stale_secs=parse_positive_int_env(
            "PM_STATUS_STALE_SECS", DEFAULT_STALE_SECS
        ),
        trusted_sources=trusted,
    )


def load_now() -> datetime:
    raw = os.environ.get("PM_STATUS_NOW", "").strip()
    if not raw:
        return datetime.now(timezone.utc)
    parsed = parse_ts(raw)
    if parsed is None:
        raise ConfigError(f"PM_STATUS_NOW is not a valid timestamp: {raw!r}")
    return parsed


def load_registry(registry_dir: Path, warnings: Warnings) -> Dict[str, RegistryRecord]:
    records: Dict[str, RegistryRecord] = {}
    if not registry_dir.exists():
        warnings.add(
            "MISSING_REGISTRY_DIR",
            "dispatch registry directory not found",
            registry_dir,
        )
        return records
    if not registry_dir.is_dir():
        warnings.add(
            "REGISTRY_NOT_DIRECTORY",
            "dispatch registry path is not a directory",
            registry_dir,
        )
        return records

    try:
        entries = list(registry_dir.iterdir())
    except OSError as exc:
        warnings.add(
            "REGISTRY_UNREADABLE",
            f"dispatch registry directory is unreadable: {exc}",
            registry_dir,
        )
        return records

    for path in sorted(entries):
        if path.suffix != ".json" or not path.is_file():
            continue
        task_id = path.stem
        if not TASK_ID_RE.match(task_id):
            warnings.add(
                "INVALID_TASK_ID_FILE",
                f"registry filename is not a valid task_id: {path.name}",
                path,
            )
            continue

        data: object = None
        error: Optional[str] = None
        replaced = False
        for attempt in (0, 1):
            try:
                with path.open(
                    "r", encoding="utf-8", errors="replace"
                ) as handle:
                    text = handle.read()
                replaced = "\ufffd" in text
                data = json.loads(text)
                error = None
                break
            except Exception as exc:  # noqa: BLE001 - tolerate concurrent writes
                error = str(exc)
                if attempt == 0:
                    time.sleep(0.02)

        if replaced:
            warnings.add(
                "REGISTRY_ENCODING_REPLACED",
                "registry contains invalid UTF-8 bytes (likely a byte-truncated "
                "brief); bytes replaced for read-only classification",
                path,
            )

        if not isinstance(data, dict):
            warnings.add(
                "REGISTRY_UNREADABLE",
                f"registry JSON is unreadable: {error or 'not an object'}",
                path,
            )
            records[task_id] = RegistryRecord(
                task_id=task_id,
                path=str(path),
                corrupt=True,
            )
            continue

        internal = data.get("task_id")
        mismatch = False
        if not isinstance(internal, str) or not internal:
            internal = task_id
            warnings.add(
                "MISSING_TASK_ID",
                "registry has no internal task_id; using filename",
                path,
            )
        elif internal != task_id:
            mismatch = True
            warnings.add(
                "TASK_ID_MISMATCH",
                f"registry filename {task_id!r} does not match internal task_id {internal!r}",
                path,
            )

        started_raw = data.get("started_at")
        started = parse_ts(started_raw)
        if started is None and started_raw not in (None, ""):
            warnings.add(
                "INVALID_STARTED_AT",
                f"registry started_at is invalid: {started_raw!r}",
                path,
            )

        host = data.get("host")
        log = data.get("log")
        records[task_id] = RegistryRecord(
            task_id=task_id,
            path=str(path),
            corrupt=mismatch,
            host=host if isinstance(host, str) else None,
            log=log if isinstance(log, str) else None,
            started_at=started,
            mismatch=mismatch,
        )
    return records


def dedupe_events(events: Iterable[Event]) -> List[Event]:
    latest: Dict[str, Event] = {}
    for event in events:
        previous = latest.get(event.kind)
        if (
            previous is None
            or event.at > previous.at
            or (event.at == previous.at and event.line > previous.line)
        ):
            latest[event.kind] = event
    return sorted(latest.values(), key=lambda event: (event.at, event.kind))


def load_ledger(
    path: Path,
    which: str,
    trusted_sources: Set[str],
    warnings: Warnings,
) -> Tuple[Dict[str, List[Event]], Set[str]]:
    events: Dict[str, List[Event]] = {}
    invalid_evidence: Set[str] = set()
    if not path.exists():
        warnings.add("MISSING_LEDGER", f"{which} ledger not found", path)
        return events, invalid_evidence

    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError as exc:
        warnings.add(
            "LEDGER_UNREADABLE",
            f"{which} ledger is unreadable: {exc}",
            path,
        )
        return events, invalid_evidence

    allowed = SENT_KINDS if which == "sent" else RECEIVED_KINDS
    with handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                warnings.add(
                    "BAD_LEDGER_LINE",
                    f"{which} ledger line is not valid JSON",
                    path,
                    line_number,
                )
                continue
            if not isinstance(record, dict):
                warnings.add(
                    "BAD_LEDGER_RECORD",
                    f"{which} ledger record is not an object",
                    path,
                    line_number,
                )
                continue

            task_id = record.get("task_id")
            if not isinstance(task_id, str) or not TASK_ID_RE.match(task_id):
                warnings.add(
                    "INVALID_LEDGER_TASK_ID",
                    f"{which} ledger task_id is invalid",
                    path,
                    line_number,
                )
                continue

            kind = record.get("kind")
            if not isinstance(kind, str) or kind not in allowed:
                warnings.add(
                    f"UNKNOWN_{which.upper()}_KIND",
                    f"{which} ledger has unknown kind: {kind!r}",
                    path,
                    line_number,
                )
                continue

            if which == "sent":
                raw_timestamp = record.get("sent_at")
                source = record.get("source")
            else:
                raw_timestamp = record.get("received_at")
                source = record.get("source")
                if not isinstance(source, str) or source not in trusted_sources:
                    warnings.add(
                        "UNTRUSTED_RECEIVED_SOURCE",
                        f"received ledger source is not trusted: {source!r}",
                        path,
                        line_number,
                    )
                    invalid_evidence.add(task_id)
                    continue

            timestamp = parse_ts(raw_timestamp)
            if timestamp is None:
                warnings.add(
                    "INVALID_TIMESTAMP",
                    f"{which} ledger timestamp is invalid: {raw_timestamp!r}",
                    path,
                    line_number,
                )
                invalid_evidence.add(task_id)
                continue

            events.setdefault(task_id, []).append(
                Event(
                    kind=kind,
                    at=timestamp,
                    source=source if isinstance(source, str) else None,
                    line=line_number,
                )
            )

    for task_id in list(events):
        events[task_id] = dedupe_events(events[task_id])
    return events, invalid_evidence


def latest_terminal(received: Sequence[Event]) -> Optional[Event]:
    candidates = [
        event for event in received if event.kind in TERMINAL_RECEIVED_KINDS
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda event: (event.at, 1 if event.kind == "done" else 0),
    )


def hint_for(state: str, flags: Sequence[str]) -> str:
    if state == "done_received":
        return "verify tracking item; receipt != resumed; status may be failed"
    if state == "failed_recorded":
        return "legacy failed result receipt; verify done.json/log; not a done delivery"
    if state == "done_sent":
        return "wait for delivery"
    if state == "done_overdue":
        return "wait for sweep; do not report yet"
    if state == "done_lost":
        return "no received; check sweep/done.json; suspected lost"
    if state == "orphan":
        return "registry missing; check dispatch record/ledger"
    if state == "unknown":
        return "registry unreadable, identity mismatch, or untrusted evidence; inspect manually"
    parts: List[str] = []
    if "failed_to_start" in flags:
        parts.append(
            "start failure reported; check hook/log; do not blindly re-dispatch"
        )
    if "possibly_hung" in flags:
        parts.append("hung reported; check log/worktree; reminder is not a verdict")
    if "stale" in flags:
        parts.append(
            "over expected duration; check log/worktree; do not auto-kill"
        )
    return "; ".join(parts) if parts else "no receipt != still running"


def classify(
    task_id: str,
    record: Optional[RegistryRecord],
    sent: Sequence[Event],
    received: Sequence[Event],
    invalid_evidence: bool,
    now: datetime,
    config: Config,
    warnings: Warnings,
) -> Optional[TaskStatus]:
    sent_done = [event for event in sent if event.kind == "done"]
    terminal = latest_terminal(received)
    flags: List[str] = []
    dispatched_age = None
    if record is not None and record.started_at is not None:
        dispatched_age = max(
            0, int((now - record.started_at).total_seconds())
        )

    if record is not None and record.corrupt:
        state = "unknown"
        actionable = True
    elif record is None:
        if terminal is not None or sent_done:
            state = "orphan"
            actionable = True
        elif sent or received or invalid_evidence:
            if invalid_evidence:
                state = "unknown"
                actionable = True
            else:
                warnings.add(
                    "ORPHAN_EVENT_IGNORED",
                    f"task {task_id} has only non-terminal events and no registry",
                )
                return None
        else:
            return None
    else:
        if terminal is not None:
            state = (
                "done_received" if terminal.kind == "done" else "failed_recorded"
            )
            actionable = False
        elif sent_done:
            latest_done_sent = max(sent_done, key=lambda event: event.at)
            age = max(0, int((now - latest_done_sent.at).total_seconds()))
            if age < config.done_overdue_secs:
                state = "done_sent"
            elif age < config.done_lost_secs:
                state = "done_overdue"
            else:
                state = "done_lost"
            actionable = state == "done_lost"
        else:
            state = "unconfirmed"
            if any(event.kind == "failed_to_start" for event in sent) or any(
                event.kind == "failed_to_start" for event in received
            ):
                flags.append("failed_to_start")
            if any(event.kind == "possibly_hung" for event in sent) or any(
                event.kind == "possibly_hung" for event in received
            ):
                flags.append("possibly_hung")
            if dispatched_age is not None and dispatched_age >= config.stale_secs:
                flags.append("stale")
            actionable = bool(flags)

    flags = [flag for flag in FLAG_ORDER if flag in flags]

    dispatched_at = record.started_at if record is not None else None
    age_secs: Optional[int] = dispatched_age
    host = record.host if record is not None else None
    log = record.log if record is not None else None
    if state == "unknown":
        dispatched_at = None
        age_secs = None
        host = None
        log = None

    if (
        record is not None
        and dispatched_at is None
        and not sent
        and not received
    ):
        warnings.add(
            "MISSING_TIMESTAMP",
            f"task {task_id} has no timestamp; included",
        )

    return TaskStatus(
        task_id=task_id,
        state=state,
        actionable=actionable,
        flags=flags,
        dispatched_at=dispatched_at,
        age_secs=age_secs,
        host=host,
        log=log,
        sent=list(sent),
        received=list(received),
        hint=hint_for(state, flags),
    )


def build_statuses(
    config: Config, now: datetime, warnings: Warnings
) -> List[TaskStatus]:
    records = load_registry(config.registry_dir, warnings)
    sent, sent_invalid = load_ledger(
        config.sent_ledger,
        "sent",
        config.trusted_sources,
        warnings,
    )
    received, received_invalid = load_ledger(
        config.received_ledger,
        "received",
        config.trusted_sources,
        warnings,
    )
    invalid = sent_invalid | received_invalid
    task_ids = sorted(set(records) | set(sent) | set(received) | invalid)

    statuses: List[TaskStatus] = []
    for task_id in task_ids:
        status = classify(
            task_id=task_id,
            record=records.get(task_id),
            sent=sent.get(task_id, []),
            received=received.get(task_id, []),
            invalid_evidence=task_id in invalid,
            now=now,
            config=config,
            warnings=warnings,
        )
        if status is not None:
            statuses.append(status)
    return statuses


def status_timestamp(status: TaskStatus) -> Optional[datetime]:
    candidates = [event.at for event in status.sent]
    candidates.extend(event.at for event in status.received)
    if status.dispatched_at is not None:
        candidates.append(status.dispatched_at)
    return max(candidates) if candidates else None


def filter_window(
    statuses: Sequence[TaskStatus],
    days: Optional[int],
    now: datetime,
    warnings: Warnings,
) -> List[TaskStatus]:
    if days is None:
        return list(statuses)
    cutoff = now - timedelta(days=days)
    filtered: List[TaskStatus] = []
    for status in statuses:
        if status.state == "unknown":
            filtered.append(status)
            continue
        timestamp = status_timestamp(status)
        if timestamp is not None:
            if timestamp >= cutoff:
                filtered.append(status)
            continue
        warnings.add(
            "MISSING_TIMESTAMP",
            f"task {status.task_id} has no timestamp; included",
        )
        filtered.append(status)
    return filtered


def format_duration(seconds: Optional[int]) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "<1m"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes}m" if minutes else f"{hours}h"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h" if hours else f"{days}d"


def last_event_text(status: TaskStatus, now: datetime) -> str:
    events: List[Tuple[str, Event]] = [
        ("sent", event) for event in status.sent
    ]
    events.extend(("recv", event) for event in status.received)
    if not events:
        return "-"
    direction, event = max(events, key=lambda item: item[1].at)
    delta = max(0, int((now - event.at).total_seconds()))
    suffix = format_duration(delta)
    if suffix == "<1m":
        suffix = "now"
    return f"{direction} {event.kind} {suffix}"


def sort_statuses(statuses: Sequence[TaskStatus]) -> List[TaskStatus]:
    return sorted(
        statuses,
        key=lambda status: (
            0 if status.actionable else 1,
            STATE_ORDER[status.state],
            -(status.age_secs or 0),
            status.task_id,
        ),
    )


def render_table(statuses: Sequence[TaskStatus], now: datetime) -> str:
    task_width = max([24] + [len(status.task_id) for status in statuses])
    state_width = max([15] + [len(status.state) for status in statuses])
    flags_width = max(
        [21] + [len(",".join(status.flags)) for status in statuses]
    )
    host_width = max(
        [12] + [len(status.host or "-") for status in statuses]
    )
    last_width = max(
        [20] + [len(last_event_text(status, now)) for status in statuses]
    )
    header = (
        f"{'TASK':<{task_width}} {'STATE':<{state_width}} "
        f"{'FLAGS':<{flags_width}} {'AGE':<8} {'HOST':<{host_width}} "
        f"{'LAST EVENT':<{last_width}} HINT"
    )
    lines = [header]
    if not statuses:
        lines.append("(no tasks)")
        return "\n".join(lines)
    for status in statuses:
        flags = ",".join(status.flags) if status.flags else "-"
        age = format_duration(status.age_secs)
        host = status.host or "-"
        lines.append(
            f"{status.task_id:<{task_width}} {status.state:<{state_width}} "
            f"{flags:<{flags_width}} {age:<8} {host:<{host_width}} "
            f"{last_event_text(status, now):<{last_width}} {status.hint}"
        )
    return "\n".join(lines)


def render_json(
    statuses: Sequence[TaskStatus],
    warnings: Warnings,
    now: datetime,
    window_days: Optional[int],
) -> dict:
    counts = {state: 0 for state in COUNT_STATES}
    for status in statuses:
        counts[status.state] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": format_ts(now),
        "window_days": window_days,
        "coverage": ["registry", "sent", "received"],
        "not_checked": ["done.json", "tracking_item"],
        "counts": counts,
        "tasks": [
            {
                "task_id": status.task_id,
                "state": status.state,
                "actionable": status.actionable,
                "flags": status.flags,
                "dispatched_at": format_ts(status.dispatched_at),
                "age_secs": status.age_secs,
                "host": status.host,
                "log": status.log,
                "sent": [
                    {"kind": event.kind, "at": format_ts(event.at)}
                    for event in status.sent
                ],
                "received": [
                    {
                        "kind": event.kind,
                        "at": format_ts(event.at),
                        "source": event.source,
                    }
                    for event in status.received
                ],
                "hint": status.hint,
            }
            for status in statuses
        ],
        "warnings": [warning.as_dict() for warning in warnings.items],
    }


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="status.sh",
        description="Read-only PM delivery status from local ledgers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a stable JSON document",
    )
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument(
        "--all",
        action="store_true",
        help="include all tasks, not just the recent window",
    )
    window_group.add_argument(
        "--days",
        type=positive_int,
        default=None,
        help="window size in days (default: PM_STATUS_WINDOW_DAYS or 7)",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="show one task_id and ignore the time window (including --days)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "exit 1 when an actionable delivery anomaly is present in the "
            "selected window; use --all for a full scan"
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.task is not None and not TASK_ID_RE.match(args.task):
        print(f"ERROR: invalid task_id: {args.task}", file=sys.stderr)
        return 2

    try:
        config = load_config()
        now = load_now()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    warnings = Warnings()
    statuses = build_statuses(config, now, warnings)

    if args.task is not None:
        statuses = [
            status for status in statuses if status.task_id == args.task
        ]
        if not statuses:
            print(f"task not found: {args.task}", file=sys.stderr)
        window_days: Optional[int] = None
    else:
        days = args.days if args.days is not None else config.window_days
        if args.all:
            days = None
        statuses = filter_window(statuses, days, now, warnings)
        window_days = None if args.all else days

    statuses = sort_statuses(statuses)

    if args.json:
        print(
            json.dumps(
                render_json(statuses, warnings, now, window_days),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_table(statuses, now))
        if warnings.items:
            print(
                f"warnings: {len(warnings.items)} (use --json for details)",
                file=sys.stderr,
            )

    if args.check and any(status.actionable for status in statuses):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
