import logging
import os
import time

import pytest

from github_activity_automation.exceptions import LockError
from github_activity_automation.runtime_lock import RunLock


def test_run_lock_creates_and_removes_lock_file(tmp_path):
    lock_file = tmp_path / "automation.lock"

    with RunLock(lock_file, stale_after_seconds=60, logger=logging.getLogger("test")):
        assert lock_file.exists()

    assert not lock_file.exists()


def test_run_lock_rejects_active_lock(tmp_path):
    lock_file = tmp_path / "automation.lock"
    lock_file.write_text("locked", encoding="utf-8")

    with pytest.raises(LockError):
        with RunLock(lock_file, stale_after_seconds=60, logger=logging.getLogger("test")):
            pass


def test_run_lock_replaces_stale_lock(tmp_path):
    lock_file = tmp_path / "automation.lock"
    lock_file.write_text("locked", encoding="utf-8")
    stale_timestamp = time.time() - 120
    os.utime(lock_file, (stale_timestamp, stale_timestamp))

    with RunLock(lock_file, stale_after_seconds=60, logger=logging.getLogger("test")):
        assert lock_file.exists()

    assert not lock_file.exists()

