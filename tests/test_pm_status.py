import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
PM_REFERENCE = TESTS_DIR.parent / "bin"
sys.path.insert(0, str(PM_REFERENCE))

import pm_status  # noqa: E402


NOW = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
NOW_STR = "2026-10-25T12:00:00Z"


def at_seconds_ago(seconds):
    return (NOW - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def at_minutes_ago(minutes):
    return at_seconds_ago(minutes * 60)


class StatusCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.registry = self.state / "dispatch-registry"
        self.registry.mkdir(parents=True)
        self.config_file = self.root / "pm.env"
        self.config_file.write_text(
            f"PM_STATE_DIR={self.state}\n"
            f"PM_REGISTRY_DIR={self.registry}\n",
            encoding="utf-8",
        )
        self.env = {
            "PM_STATE_DIR": str(self.state),
            "PM_REGISTRY_DIR": str(self.registry),
            "PM_STATUS_NOW": NOW_STR,
            "PM_STATUS_TRUSTED_SOURCES": "pm,PM,watchdog",
        }

    def tearDown(self):
        for directory in (self.state, self.registry):
            try:
                directory.chmod(0o755)
            except OSError:
                pass
        self.tmp.cleanup()

    def write_registry(
        self,
        task_id,
        *,
        started_at="__default__",
        internal="__default__",
        host="worker",
        log=None,
        extra=None,
    ):
        data = {
            "task_id": task_id if internal == "__default__" else internal,
            "host": host,
            "log": log or f"/tmp/{task_id}.log",
        }
        if started_at == "__default__":
            started_at = at_minutes_ago(10)
        if started_at is not None:
            data["started_at"] = started_at
        if internal == "":
            data.pop("task_id", None)
        if extra:
            data.update(extra)
        (self.registry / f"{task_id}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def write_corrupt_registry(self, task_id):
        (self.registry / f"{task_id}.json").write_text(
            "{not-json", encoding="utf-8"
        )

    def append_ledger(self, name, record):
        path = self.state / name
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def write_sent(self, task_id, kind, *, at="__default__", source="hook"):
        if at == "__default__":
            at = at_minutes_ago(10)
        self.append_ledger(
            "handoff-sent.jsonl",
            {
                "task_id": task_id,
                "kind": kind,
                "sent_at": at,
                "source": source,
            },
        )

    def write_received(self, task_id, kind, *, at="__default__", source="pm"):
        if at == "__default__":
            at = at_minutes_ago(5)
        self.append_ledger(
            "handoff-received.jsonl",
            {
                "task_id": task_id,
                "kind": kind,
                "received_at": at,
                "source": source,
            },
        )

    def run_cli(self, *args, env=None):
        merged = dict(self.env)
        if env:
            merged.update(env)
        with mock.patch.dict(os.environ, merged, clear=True):
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = pm_status.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def json_result(self, *args, env=None):
        code, out, err = self.run_cli("--json", *args, env=env)
        return code, json.loads(out), err

    def task(self, document, task_id):
        for item in document["tasks"]:
            if item["task_id"] == task_id:
                return item
        self.fail(f"task {task_id} not in {document['tasks']!r}")

    def state_of(self, task_id, *args, env=None):
        _, document, _ = self.json_result(*args, env=env)
        return self.task(document, task_id)["state"]

    def warning_codes(self, document):
        return {warning["code"] for warning in document["warnings"]}


class StatusClassificationTests(StatusCase):
    def test_unconfirmed(self):
        self.write_registry("task-a")
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertFalse(status["actionable"])
        self.assertEqual(status["flags"], [])
        self.assertIsNotNone(status["age_secs"])

    def test_done_sent(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.assertEqual(self.state_of("task-a"), "done_sent")

    def test_done_overdue_at_90_minutes(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(5400))
        self.assertEqual(self.state_of("task-a"), "done_overdue")

    def test_done_lost_at_130_minutes(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(7800))
        code, document, _ = self.json_result("--check")
        status = self.task(document, "task-a")
        self.assertEqual(status["state"], "done_lost")
        self.assertTrue(status["actionable"])
        self.assertEqual(code, 1)

    def test_threshold_boundaries(self):
        self.write_registry("overdue")
        self.write_sent("overdue", "done", at=at_seconds_ago(3600))
        self.write_registry("lost")
        self.write_sent("lost", "done", at=at_seconds_ago(7200))
        _, document, _ = self.json_result()
        self.assertEqual(self.task(document, "overdue")["state"], "done_overdue")
        self.assertEqual(self.task(document, "lost")["state"], "done_lost")

    def test_done_received(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(2400))
        self.write_received("task-a", "done", at=at_seconds_ago(2280))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "done_received")
        self.assertFalse(status["actionable"])
        self.assertIn("receipt != resumed", status["hint"])

    def test_received_done_without_sent(self):
        self.write_registry("task-a")
        self.write_received("task-a", "done", at=at_seconds_ago(60))
        self.assertEqual(self.state_of("task-a"), "done_received")

    def test_received_done_without_registry_is_orphan(self):
        self.write_received("task-a", "done", at=at_minutes_ago(60))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "orphan")
        self.assertTrue(status["actionable"])
        self.assertEqual(status["received"][0]["kind"], "done")

    def test_sent_done_without_registry_is_orphan(self):
        self.write_sent("task-a", "done", at=at_minutes_ago(10))
        self.assertEqual(self.state_of("task-a"), "orphan")

    def test_check_reminder_does_not_make_orphan(self):
        self.write_sent("task-a", "check_reminder", at=at_minutes_ago(5))
        code, document, _ = self.json_result("--check")
        self.assertEqual(code, 0)
        self.assertEqual(document["tasks"], [])
        self.assertIn("ORPHAN_EVENT_IGNORED", self.warning_codes(document))

    def test_done_sent_with_received_check_reminder_stays_done_sent(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "check_reminder", at=at_seconds_ago(300))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "done_sent")
        self.assertEqual(status["flags"], [])

    def test_received_failed_outranks_sent_done(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "failed", at=at_seconds_ago(300))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "failed_recorded")
        self.assertFalse(status["actionable"])
        self.assertIn("legacy failed result receipt", status["hint"])

    def test_received_failed_only(self):
        self.write_registry("task-a")
        self.write_received("task-a", "failed", at=at_seconds_ago(300))
        self.assertEqual(self.state_of("task-a"), "failed_recorded")

    def test_latest_terminal_receipt_wins_done(self):
        self.write_registry("task-a")
        self.write_received("task-a", "failed", at=at_seconds_ago(600))
        self.write_received("task-a", "done", at=at_seconds_ago(300))
        self.assertEqual(self.state_of("task-a"), "done_received")

    def test_latest_terminal_receipt_wins_failed(self):
        self.write_registry("task-a")
        self.write_received("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "failed", at=at_seconds_ago(300))
        self.assertEqual(self.state_of("task-a"), "failed_recorded")

    def test_received_failed_from_hook_is_ignored(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received(
            "task-a", "failed", at=at_seconds_ago(300), source="hook"
        )
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "done_sent")
        self.assertIn("UNTRUSTED_RECEIVED_SOURCE", self.warning_codes(self.json_result()[1]))

    def test_received_failed_without_registry_is_orphan(self):
        self.write_received("task-a", "failed", at=at_minutes_ago(30))
        self.assertEqual(self.state_of("task-a"), "orphan")


class FlagTests(StatusCase):
    def test_sent_failed_to_start(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "failed_to_start", at=at_minutes_ago(20))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertEqual(status["flags"], ["failed_to_start"])
        self.assertTrue(status["actionable"])

    def test_received_failed_to_start(self):
        self.write_registry("task-a")
        self.write_received(
            "task-a", "failed_to_start", at=at_minutes_ago(20)
        )
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], ["failed_to_start"])

    def test_untrusted_received_failed_to_start_is_ignored(self):
        self.write_registry("task-a")
        self.write_received(
            "task-a", "failed_to_start", at=at_minutes_ago(20), source="hook"
        )
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], [])
        self.assertIn(
            "UNTRUSTED_RECEIVED_SOURCE", self.warning_codes(self.json_result()[1])
        )

    def test_sent_possibly_hung(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "possibly_hung", at=at_minutes_ago(20))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], ["possibly_hung"])

    def test_received_possibly_hung(self):
        self.write_registry("task-a")
        self.write_received("task-a", "possibly_hung", at=at_minutes_ago(20))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], ["possibly_hung"])

    def test_untrusted_received_possibly_hung_is_ignored(self):
        self.write_registry("task-a")
        self.write_received(
            "task-a", "possibly_hung", at=at_minutes_ago(20), source="hook"
        )
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], [])

    def test_check_reminder_is_not_a_flag(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "check_reminder", at=at_minutes_ago(5))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertEqual(status["flags"], [])
        self.assertEqual(status["sent"][0]["kind"], "check_reminder")

    def test_stale(self):
        self.write_registry("task-a", started_at=at_seconds_ago(10800))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["flags"], ["stale"])
        self.assertTrue(status["actionable"])

    def test_terminal_states_suppress_flags(self):
        self.write_registry("done")
        self.write_sent("done", "done", at=at_seconds_ago(600))
        self.write_sent("done", "failed_to_start", at=at_seconds_ago(900))
        self.write_registry("overdue")
        self.write_sent("overdue", "done", at=at_seconds_ago(5400))
        self.write_sent("overdue", "possibly_hung", at=at_seconds_ago(6000))
        self.write_registry("received")
        self.write_received("received", "done", at=at_seconds_ago(600))
        self.write_sent("received", "failed_to_start", at=at_seconds_ago(900))
        self.write_registry("failed")
        self.write_received("failed", "failed", at=at_seconds_ago(600))
        self.write_sent("failed", "failed_to_start", at=at_seconds_ago(900))
        _, document, _ = self.json_result()
        for task_id in ("done", "overdue", "received", "failed"):
            self.assertEqual(self.task(document, task_id)["flags"], [], task_id)


class SourceTests(StatusCase):
    def test_untrusted_received_done_without_registry_is_unknown(self):
        self.write_received("task-a", "done", at=at_minutes_ago(10), source="hook")
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unknown")
        self.assertIn(
            "UNTRUSTED_RECEIVED_SOURCE", self.warning_codes(self.json_result()[1])
        )

    def test_untrusted_received_done_with_registry_is_unconfirmed(self):
        self.write_registry("task-a")
        self.write_received("task-a", "done", at=at_minutes_ago(10), source="hook")
        self.assertEqual(self.state_of("task-a"), "unconfirmed")

    def test_untrusted_received_done_with_sent_done_stays_done_sent(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "done", at=at_seconds_ago(300), source="hook")
        self.assertEqual(self.state_of("task-a"), "done_sent")

    def test_unknown_received_source_is_ignored(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "done", at=at_seconds_ago(300), source="agent")
        self.assertEqual(self.state_of("task-a"), "done_sent")


class WindowAndCliTests(StatusCase):
    def test_window_and_all_and_task(self):
        self.write_registry("old", started_at=at_seconds_ago(10 * 86400))
        self.write_registry("recent", started_at=at_seconds_ago(600))
        _, default_doc, _ = self.json_result()
        self.assertEqual({t["task_id"] for t in default_doc["tasks"]}, {"recent"})
        _, all_doc, _ = self.json_result("--all")
        self.assertEqual({t["task_id"] for t in all_doc["tasks"]}, {"old", "recent"})
        _, days_doc, _ = self.json_result("--days", "30")
        self.assertEqual({t["task_id"] for t in days_doc["tasks"]}, {"old", "recent"})
        _, task_doc, _ = self.json_result("--task", "old")
        self.assertEqual([t["task_id"] for t in task_doc["tasks"]], ["old"])
        _, task_days_doc, _ = self.json_result("--task", "old", "--days", "1")
        self.assertEqual([t["task_id"] for t in task_days_doc["tasks"]], ["old"])

    def test_invalid_days_and_mutual_exclusion(self):
        for args in (("--days", "0"), ("--days", "x"), ("--days", "1", "--all")):
            with self.assertRaises(SystemExit) as raised:
                self.run_cli(*args)
            self.assertEqual(raised.exception.code, 2)

    def test_invalid_task_id_returns_2(self):
        code, _, err = self.run_cli("--task", "../x")
        self.assertEqual(code, 2)
        self.assertIn("invalid task_id", err)

    def test_missing_task_returns_0(self):
        code, out, err = self.run_cli("--task", "missing", "--json", "--check")
        self.assertEqual(code, 0)
        self.assertIn("task not found", err)
        self.assertEqual(json.loads(out)["tasks"], [])

    def test_window_uses_latest_receipt_for_old_registry(self):
        self.write_registry("task-a", started_at=at_seconds_ago(10 * 86400))
        self.write_received("task-a", "done", at=at_seconds_ago(600))
        _, document, _ = self.json_result()
        self.assertEqual(self.task(document, "task-a")["state"], "done_received")

    def test_missing_started_at_is_included_with_warning(self):
        self.write_registry("task-a", started_at=None)
        _, document, _ = self.json_result()
        status = self.task(document, "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertIsNone(status["age_secs"])
        self.assertIn("MISSING_TIMESTAMP", self.warning_codes(document))

    def test_registry_task_id_mismatch_is_unknown(self):
        self.write_registry("file-name", internal="other-name")
        _, document, _ = self.json_result()
        status = self.task(document, "file-name")
        self.assertEqual(status["state"], "unknown")
        self.assertIn("TASK_ID_MISMATCH", self.warning_codes(document))
        self.assertIsNone(status["dispatched_at"])
        self.assertIsNone(status["age_secs"])
        self.assertIsNone(status["host"])
        self.assertIsNone(status["log"])

    def test_corrupt_registry_fields_are_null(self):
        self.write_corrupt_registry("corrupt")
        _, document, _ = self.json_result()
        status = self.task(document, "corrupt")
        self.assertEqual(status["state"], "unknown")
        self.assertIsNone(status["dispatched_at"])
        self.assertIsNone(status["age_secs"])
        self.assertIsNone(status["host"])
        self.assertIsNone(status["log"])

    def test_registry_directory_unreadable_warns(self):
        self.write_registry("task-a")
        self.registry.chmod(0o000)
        try:
            _, document, _ = self.json_result()
        finally:
            self.registry.chmod(0o755)
        self.assertEqual(document["tasks"], [])
        self.assertIn("REGISTRY_UNREADABLE", self.warning_codes(document))

    def test_registry_invalid_utf8_brief_recovers(self):
        payload = (
            b'{"task_id":"task-a","host":"worker",'
            b'"log":"/tmp/task-a.log","started_at":"'
            + at_minutes_ago(10).encode()
            + b'","brief":"'
            + b"\xe4\xb8"
            + b'"}'
        )
        (self.registry / "task-a.json").write_bytes(payload)
        _, document, _ = self.json_result()
        status = self.task(document, "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertEqual(status["host"], "worker")
        self.assertEqual(status["log"], "/tmp/task-a.log")
        self.assertIn(
            "REGISTRY_ENCODING_REPLACED", self.warning_codes(document)
        )

    def test_registry_missing_internal_task_id_uses_filename(self):
        self.write_registry("file-name", internal="")
        _, document, _ = self.json_result()
        status = self.task(document, "file-name")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertIn("MISSING_TASK_ID", self.warning_codes(document))


class JsonAndCountTests(StatusCase):
    def test_json_schema_and_no_brief(self):
        self.write_registry(
            "task-a",
            extra={"brief": "SECRET-BRIEF", "origin_chat_id": "uuid"},
        )
        self.write_sent("task-a", "done", at=at_seconds_ago(600))
        self.write_received("task-a", "done", at=at_seconds_ago(300))
        code, out, err = self.run_cli("--json")
        self.assertEqual(code, 0)
        document = json.loads(out)
        self.assertNotIn("SECRET-BRIEF", out)
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["coverage"], ["registry", "sent", "received"])
        self.assertEqual(document["not_checked"], ["done.json", "tracking_item"])
        for key in (
            "task_id",
            "state",
            "actionable",
            "flags",
            "dispatched_at",
            "age_secs",
            "host",
            "log",
            "sent",
            "received",
            "hint",
        ):
            self.assertIn(key, document["tasks"][0])

    def test_json_check_exit_code(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(7800))
        code, out, _ = self.run_cli("--json", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["tasks"][0]["state"], "done_lost")

    def test_check_matrix(self):
        self.write_registry("lost")
        self.write_sent("lost", "done", at=at_seconds_ago(7800))
        self.assertEqual(self.run_cli("--check")[0], 1)

        self.write_received("failed-task", "failed", at=at_seconds_ago(600), source="pm")
        self.write_registry("failed-task")
        code, _, _ = self.run_cli("--check", "--task", "failed-task")
        self.assertEqual(code, 0)

        self.write_corrupt_registry("corrupt")
        self.assertEqual(self.run_cli("--check", "--task", "corrupt")[0], 1)

        self.write_registry("stale", started_at=at_seconds_ago(10800))
        self.assertEqual(self.run_cli("--check", "--task", "stale")[0], 1)

        self.write_registry("reminder")
        self.write_sent("reminder", "check_reminder", at=at_minutes_ago(5))
        self.assertEqual(self.run_cli("--check", "--task", "reminder")[0], 0)

    def test_check_orphan_and_alert_flags(self):
        self.write_received("orphan", "done", at=at_seconds_ago(600))
        self.assertEqual(self.run_cli("--check", "--task", "orphan")[0], 1)

        self.write_registry("start")
        self.write_sent("start", "failed_to_start", at=at_seconds_ago(600))
        self.assertEqual(self.run_cli("--check", "--task", "start")[0], 1)

        self.write_registry("hung")
        self.write_sent("hung", "possibly_hung", at=at_seconds_ago(600))
        self.assertEqual(self.run_cli("--check", "--task", "hung")[0], 1)

    def test_terminal_tie_done_wins(self):
        self.write_registry("task-a")
        same = at_seconds_ago(600)
        self.write_received("task-a", "done", at=same)
        self.write_received("task-a", "failed", at=same)
        self.assertEqual(self.state_of("task-a"), "done_received")

    def test_check_default_window_hides_old_done_lost(self):
        self.write_registry("old", started_at=at_seconds_ago(10 * 86400))
        self.write_sent("old", "done", at=at_seconds_ago(10 * 86400))
        self.assertEqual(self.run_cli("--check")[0], 0)
        self.assertEqual(self.run_cli("--all", "--check")[0], 1)

    def test_window_days_null_for_all_and_task(self):
        self.write_registry("task-a")
        _, default_doc, _ = self.json_result()
        self.assertEqual(default_doc["window_days"], 7)
        _, all_doc, _ = self.json_result("--all")
        self.assertIsNone(all_doc["window_days"])
        _, task_doc, _ = self.json_result("--task", "task-a")
        self.assertIsNone(task_doc["window_days"])

    def test_invalid_window_env_returns_2(self):
        code, _, err = self.run_cli(
            "--json", env={"PM_STATUS_WINDOW_DAYS": "0"}
        )
        self.assertEqual(code, 2)
        self.assertIn("PM_STATUS_WINDOW_DAYS", err)

    def test_invalid_utf8_ledger_is_a_warning(self):
        self.write_registry("task-a")
        with (self.state / "handoff-sent.jsonl").open("wb") as handle:
            handle.write(b"\xff\xfe\n")
        code, document, _ = self.json_result()
        self.assertEqual(code, 0)
        self.assertEqual(self.task(document, "task-a")["state"], "unconfirmed")
        self.assertTrue(
            {"BAD_LEDGER_LINE", "LEDGER_UNREADABLE"}
            & self.warning_codes(document)
        )

    def test_failed_recorded_is_visibility_only_for_old_and_new(self):
        self.write_registry("old")
        self.write_received("old", "failed", at=at_seconds_ago(10 * 86400))
        self.write_registry("new")
        self.write_received("new", "failed", at=at_seconds_ago(600))
        code, document, _ = self.json_result("--check", "--all")
        self.assertEqual(code, 0)
        self.assertEqual(self.task(document, "old")["state"], "failed_recorded")
        self.assertEqual(self.task(document, "new")["state"], "failed_recorded")
        self.assertFalse(self.task(document, "old")["actionable"])

    def test_counts(self):
        self.write_registry("running")
        self.write_registry("lost")
        self.write_sent("lost", "done", at=at_seconds_ago(7800))
        self.write_registry("failed")
        self.write_received("failed", "failed", at=at_seconds_ago(600))
        _, document, _ = self.json_result()
        self.assertEqual(document["counts"]["unconfirmed"], 1)
        self.assertEqual(document["counts"]["done_lost"], 1)
        self.assertEqual(document["counts"]["failed_recorded"], 1)
        self.assertEqual(sum(document["counts"].values()), 3)

    def test_duplicate_sent_done_keeps_latest(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(1200))
        self.write_sent("task-a", "done", at=at_seconds_ago(300))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "done_sent")
        self.assertEqual(len(status["sent"]), 1)
        self.assertEqual(status["sent"][0]["at"], at_seconds_ago(300))

    def test_unknown_kind_warns_and_is_ignored(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "weird", at=at_seconds_ago(300))
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertEqual(status["sent"], [])
        self.assertIn("UNKNOWN_SENT_KIND", self.warning_codes(self.json_result()[1]))

    def test_bad_ledger_line_does_not_break_other_tasks(self):
        self.write_registry("task-a")
        with (self.state / "handoff-sent.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{bad-json\n")
        _, document, _ = self.json_result()
        self.assertEqual(self.task(document, "task-a")["state"], "unconfirmed")
        self.assertIn("BAD_LEDGER_LINE", self.warning_codes(document))

    def test_empty_state_is_clean(self):
        code, document, _ = self.json_result()
        self.assertEqual(code, 0)
        self.assertEqual(document["tasks"], [])
        self.assertTrue(document["warnings"])
        self.assertEqual(sum(document["counts"].values()), 0)

    def test_read_only(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at=at_seconds_ago(600))

        def snapshot():
            paths = [self.state, *sorted(self.state.rglob("*"))]
            return {
                str(path): (
                    path.is_dir(),
                    path.stat().st_mtime_ns,
                    None if path.is_dir() else path.read_bytes(),
                )
                for path in paths
            }

        before = snapshot()
        self.state.chmod(0o555)
        self.registry.chmod(0o555)
        try:
            code, _, _ = self.run_cli()
        finally:
            self.state.chmod(0o755)
            self.registry.chmod(0o755)
        self.assertEqual(code, 0)
        self.assertEqual(before, snapshot())


class TimestampTests(StatusCase):
    def test_parse_timestamp_formats(self):
        self.assertEqual(
            pm_status.parse_ts("2026-10-25T12:00:00Z"),
            NOW,
        )
        self.assertEqual(
            pm_status.parse_ts("2026-10-25T12:00:00+00:00"),
            NOW,
        )
        self.assertEqual(
            pm_status.parse_ts("2026-10-25T12:00:00"),
            NOW,
        )
        self.assertEqual(pm_status.parse_ts(NOW.timestamp()), NOW)
        self.assertEqual(
            pm_status.parse_ts("2026-10-25T12:00:00.5Z"),
            NOW + timedelta(seconds=0.5),
        )
        self.assertEqual(
            pm_status.parse_ts("2026-10-25T12:00:00.1234567Z"),
            NOW + timedelta(seconds=0.123456),
        )
        self.assertIsNone(pm_status.parse_ts("not-a-time"))

    def test_invalid_pm_status_now_returns_2(self):
        code, _, err = self.run_cli(
            "--json", env={"PM_STATUS_NOW": "not-a-time"}
        )
        self.assertEqual(code, 2)
        self.assertIn("PM_STATUS_NOW", err)

    def test_invalid_sent_done_timestamp_with_registry_is_unconfirmed(self):
        self.write_registry("task-a")
        self.write_sent("task-a", "done", at="not-a-time")
        status = self.task(self.json_result()[1], "task-a")
        self.assertEqual(status["state"], "unconfirmed")
        self.assertIn("INVALID_TIMESTAMP", self.warning_codes(self.json_result()[1]))

    def test_invalid_sent_done_timestamp_without_registry_is_unknown(self):
        self.write_sent("task-a", "done", at="not-a-time")
        self.assertEqual(self.state_of("task-a"), "unknown")


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wrapper_dir = self.root / "wrapper"
        self.wrapper_dir.mkdir()
        self.state = self.root / "state"
        self.registry = self.state / "dispatch-registry"
        self.registry.mkdir(parents=True)
        self.config = self.root / "pm.env"
        self.config.write_text(
            f"PM_STATE_DIR={self.state}\n"
            f"PM_REGISTRY_DIR={self.registry}\n",
            encoding="utf-8",
        )
        shutil.copy2(PM_REFERENCE / "status.sh", self.wrapper_dir / "status.sh")
        shutil.copy2(PM_REFERENCE / "pm-config.sh", self.wrapper_dir / "pm-config.sh")
        shutil.copy2(PM_REFERENCE / "pm_status.py", self.wrapper_dir / "pm_status.py")

    def tearDown(self):
        self.tmp.cleanup()

    def wrapper_env(self, **extra):
        env = os.environ.copy()
        env.update(
            {
                "PM_CONFIG": str(self.config),
                "HOME": str(self.root / "home"),
                "XDG_CONFIG_HOME": str(self.root / "xdg"),
                "PM_STATUS_NOW": NOW_STR,
            }
        )
        env.update(extra)
        return env

    def run_wrapper(self, args=("--json",), env=None, wrapper_dir=None):
        target = (wrapper_dir or self.wrapper_dir) / "status.sh"
        return subprocess.run(
            ["/bin/bash", str(target), *args],
            env=env or self.wrapper_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_missing_pm_config(self):
        only_wrapper = self.root / "only-wrapper"
        only_wrapper.mkdir()
        shutil.copy2(PM_REFERENCE / "status.sh", only_wrapper / "status.sh")
        result = self.run_wrapper(wrapper_dir=only_wrapper)
        self.assertEqual(result.returncode, 2)
        self.assertIn("pm-config.sh", result.stderr)

    def test_missing_pm_env(self):
        env = self.wrapper_env(
            PM_CONFIG=str(self.root / "missing.env"),
            HOME=str(self.root / "empty-home"),
            XDG_CONFIG_HOME=str(self.root / "empty-xdg"),
        )
        result = self.run_wrapper(env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no pm.env", result.stderr)

    def test_empty_state_dir_in_config_exits_2(self):
        empty_config = self.root / "empty.env"
        empty_config.write_text(
            "PM_STATE_DIR=\n"
            f"PM_REGISTRY_DIR={self.registry}\n",
            encoding="utf-8",
        )
        result = self.run_wrapper(env=self.wrapper_env(PM_CONFIG=str(empty_config)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be non-empty", result.stderr)

    def test_missing_python3(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "dirname").symlink_to("/usr/bin/dirname")
        env = self.wrapper_env(PATH=str(bin_dir))
        result = self.run_wrapper(env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("python3", result.stderr)

    def test_env_is_scrubbed(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        dump = self.root / "env.txt"
        fake_python = bin_dir / "python3"
        fake_python.write_text(
            "#!/bin/bash\n"
            f"env > {dump}\n"
            "exit 0\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        env = self.wrapper_env(
            PATH=f"{bin_dir}:/usr/bin:/bin",
            PM_NTFY_PASS="secret",
            PM_SSH_KEY="secret",
            PM_SHEETS_API_KEY="secret",
        )
        result = self.run_wrapper(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        dumped = dump.read_text(encoding="utf-8")
        self.assertNotIn("PM_NTFY_PASS", dumped)
        self.assertNotIn("PM_SSH_KEY", dumped)
        self.assertNotIn("PM_SHEETS_API_KEY", dumped)
        self.assertNotIn("PM_CONFIG", dumped)
        self.assertIn("PM_STATE_DIR", dumped)
        self.assertIn("PYTHONIOENCODING=utf-8", dumped)

    def test_no_ssh_or_curl_calls(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        marker = self.root / "network-called"
        for name in ("ssh", "curl"):
            script = bin_dir / name
            script.write_text(
                "#!/bin/bash\n"
                f"touch {marker}\n"
                "exit 1\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
        env = self.wrapper_env(PATH=f"{bin_dir}:/usr/bin:/bin")
        result = self.run_wrapper(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
