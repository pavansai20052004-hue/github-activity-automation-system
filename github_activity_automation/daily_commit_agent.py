from __future__ import annotations

import logging
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import load_config, require_env
from .exceptions import AutomationError
from .github_client import GitHubClient
from .logging_setup import configure_logging
from .repository_selector import select_repository
from .runtime_lock import RunLock
from .state import AutomationState


ACTIVITY_MARKER_LENGTH = 12


def run_daily_commit(config_path: str | Path = "config.json", force: bool = False, dry_run: bool = False) -> int:
    try:
        config = load_config(config_path)
        logger = configure_logging(config.log_file, config.log_level).getChild("daily_commit")
    except AutomationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if config.kill_switch_active:
        logger.warning("Kill switch active; Daily Commit Agent stopped before API calls", extra={"event": "kill_switch"})
        return 0

    try:
        with RunLock(config.runtime.lock_file, config.runtime.lock_stale_after_seconds, logger):
            return _run_daily_commit_with_lock(config, logger, force=force, dry_run=dry_run)
    except AutomationError as exc:
        logger.error("Daily Commit Agent failed", extra={"event": "daily_commit.failed", "error": str(exc)})
        return 1
    except Exception:
        logger.exception("Unexpected Daily Commit Agent failure", extra={"event": "daily_commit.unexpected_failure"})
        return 1


def _run_daily_commit_with_lock(config, logger: logging.Logger, force: bool, dry_run: bool) -> int:
    state = AutomationState.load(config.state_file)
    today = date.today()
    if not state.should_run_daily(today, force=force):
        logger.info("Daily Commit Agent already ran today", extra={"event": "daily_commit.noop"})
        return 0

    token = require_env(config.secrets.github_token_env)
    client = GitHubClient(
        token=token,
        api_base_url=config.github.api_base_url,
        timeout_seconds=config.github.request_timeout_seconds,
        max_retries=config.github.max_retries,
        retry_backoff_seconds=config.github.retry_backoff_seconds,
        logger=logger,
    )

    repositories = client.list_owned_repositories()
    repository = select_repository(
        repositories,
        state.last_daily_repository,
        config.daily_commit.excluded_repositories,
    )
    repository_full_name = str(repository["full_name"])
    repository_name = str(repository["name"])
    logger.info(
        "Selected repository for daily activity",
        extra={"event": "daily_commit.repository_selected", "repository": repository_full_name},
    )

    commit_total = random.SystemRandom().randint(
        config.daily_commit.min_commits,
        config.daily_commit.max_commits,
    )
    messages = random.SystemRandom().sample(list(config.daily_commit.commit_messages), commit_total)

    if dry_run:
        logger.info(
            "Dry run complete; no commits or state changes were written",
            extra={
                "event": "daily_commit.dry_run",
                "repository": repository_full_name,
                "target_file": config.daily_commit.target_file,
                "planned_commits": commit_total,
                "messages": messages,
            },
        )
        return 0

    existing_file = client.get_file(repository_full_name, config.daily_commit.target_file)
    content = existing_file.content if existing_file else ""
    sha = existing_file.sha if existing_file else None

    for index, message in enumerate(messages, start=1):
        content = _append_activity_entry(content, repository_full_name, index, commit_total)
        result = client.put_file(
            repository_full_name=repository_full_name,
            file_path=config.daily_commit.target_file,
            message=message,
            content=content,
            sha=sha,
        )
        sha = result.get("content", {}).get("sha")
        logger.info(
            "Created activity commit",
            extra={
                "event": "daily_commit.commit_created",
                "repository": repository_full_name,
                "commit_index": index,
                "commit_total": commit_total,
            },
        )

    state.mark_daily_run(today, repository_name)
    state.save()
    logger.info(
        "Daily Commit Agent completed",
        extra={"event": "daily_commit.completed", "repository": repository_full_name, "commits": commit_total},
    )
    return 0


def _append_activity_entry(content: str, repository_full_name: str, index: int, commit_total: int) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    marker = uuid4().hex[:ACTIVITY_MARKER_LENGTH]
    line = (
        f"{timestamp} | repository={repository_full_name} | "
        f"entry={index}/{commit_total} | marker={marker}"
    )
    prefix = content.rstrip("\n")
    return f"{prefix}\n{line}\n" if prefix else f"{line}\n"
