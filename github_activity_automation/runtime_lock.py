from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

from .exceptions import LockError


class RunLock:
    """Cross-platform lock file for scheduled runs.

    The lock is intentionally simple: create a file exclusively, write metadata,
    and remove it on exit. A stale lock can be replaced after the configured age.
    """

    def __init__(self, path: Path, stale_after_seconds: int, logger: logging.Logger) -> None:
        self.path = path
        self.stale_after_seconds = stale_after_seconds
        self.logger = logger
        self._acquired = False

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._acquired = False

    def _acquire(self) -> None:
        try:
            self._write_lock_file()
            self._acquired = True
        except FileExistsError:
            if self._is_stale():
                self.logger.warning(
                    "Removing stale runtime lock",
                    extra={"event": "runtime_lock.stale_removed", "lock_file": str(self.path)},
                )
                self.path.unlink(missing_ok=True)
                self._write_lock_file()
                self._acquired = True
                return
            raise LockError(f"Another automation run is already active: {self.path}")

    def _write_lock_file(self) -> None:
        metadata = {
            "pid": os.getpid(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        with os.fdopen(os.open(self.path, flags), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle)

    def _is_stale(self) -> bool:
        try:
            modified_at = datetime.fromtimestamp(self.path.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            return False
        age = datetime.now(timezone.utc) - modified_at
        return age.total_seconds() > self.stale_after_seconds
