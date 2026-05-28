from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

from .config import load_config, require_env
from .content_provider import ProjectIdea, get_project_idea
from .exceptions import AutomationError, GitHubAPIError
from .github_client import GitHubClient
from .logging_setup import configure_logging
from .project_templates import SUPPORTED_LANGUAGES, build_project_files
from .runtime_lock import RunLock
from .state import AutomationState


MAX_REPOSITORY_NAME_LENGTH = 80
REPOSITORY_NAME_SUFFIX_LENGTH = 6


def run_project_creator(
    config_path: str | Path = "config.json",
    force: bool = False,
    language: str | None = None,
    dry_run: bool = False,
) -> int:
    try:
        config = load_config(config_path)
        logger = configure_logging(config.log_file, config.log_level).getChild("project_creator")
    except AutomationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if config.kill_switch_active:
        logger.warning("Kill switch active; Project Creator Agent stopped before API calls", extra={"event": "kill_switch"})
        return 0

    selected_language = (language or config.project_creator.default_language).lower()
    if selected_language not in config.project_creator.languages:
        logger.error(
            "Requested language is not enabled in config",
            extra={"event": "project_creator.invalid_language", "language": selected_language},
        )
        return 2
    if selected_language not in SUPPORTED_LANGUAGES:
        logger.error(
            "Requested language has no template implementation",
            extra={"event": "project_creator.unsupported_language", "language": selected_language},
        )
        return 2

    try:
        with RunLock(config.runtime.lock_file, config.runtime.lock_stale_after_seconds, logger):
            return _run_project_creator_with_lock(
                config=config,
                logger=logger,
                force=force,
                language=selected_language,
                dry_run=dry_run,
            )
    except AutomationError as exc:
        logger.error("Project Creator Agent failed", extra={"event": "project_creator.failed", "error": str(exc)})
        return 1
    except Exception:
        logger.exception("Unexpected Project Creator Agent failure", extra={"event": "project_creator.unexpected_failure"})
        return 1


def _run_project_creator_with_lock(config, logger, force: bool, language: str, dry_run: bool) -> int:
    state = AutomationState.load(config.state_file)
    today = date.today()
    if not state.should_create_project(today, config.project_creator.frequency_days, force=force):
        logger.info("Project Creator Agent interval has not elapsed", extra={"event": "project_creator.noop"})
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
    user = client.get_authenticated_user()
    owner = str(user["login"])

    idea = get_project_idea(
        config.project_creator,
        config.secrets,
        config.github.request_timeout_seconds,
        state.created_project_names(),
        logger,
    )

    if dry_run:
        repository_name = _avoid_local_duplicates(
            _slugify(f"{config.project_creator.name_prefix}-{idea.title}"),
            state.created_project_names(),
        )
        files = build_project_files(repository_name, idea, language)
        logger.info(
            "Dry run complete; no repository, files, or state changes were written",
            extra={
                "event": "project_creator.dry_run",
                "repository": f"{owner}/{repository_name}",
                "language": language,
                "planned_files": [file.path for file in files],
            },
        )
        return 0

    repository_name = _create_unique_repository(
        client=client,
        idea=idea,
        owner=owner,
        prefix=config.project_creator.name_prefix,
        existing_names=state.created_project_names(),
        private=config.project_creator.visibility == "private",
        retry_limit=config.project_creator.name_retry_limit,
        logger=logger,
    )

    repository_full_name = f"{owner}/{repository_name}"
    for file in build_project_files(repository_name, idea, language):
        client.put_file(
            repository_full_name=repository_full_name,
            file_path=file.path,
            message=f"chore: add {file.path}",
            content=file.content,
        )
        logger.info(
            "Seeded project file",
            extra={"event": "project_creator.file_seeded", "repository": repository_full_name, "path": file.path},
        )

    repository_url = f"https://github.com/{repository_full_name}"
    state.record_created_project(repository_name, repository_url, language, today=today)
    state.save()
    logger.info(
        "Project Creator Agent completed",
        extra={
            "event": "project_creator.completed",
            "repository": repository_full_name,
            "url": repository_url,
            "language": language,
        },
    )
    return 0


def _create_unique_repository(
    client: GitHubClient,
    idea: ProjectIdea,
    owner: str,
    prefix: str,
    existing_names: set[str],
    private: bool,
    retry_limit: int,
    logger,
) -> str:
    base_name = _slugify(f"{prefix}-{idea.title}")
    candidate = _avoid_local_duplicates(base_name, existing_names)

    for attempt in range(1, retry_limit + 1):
        try:
            client.create_repository(candidate, idea.description, private=private)
            logger.info(
                "Created GitHub repository",
                extra={"event": "project_creator.repository_created", "repository": f"{owner}/{candidate}"},
            )
            return candidate
        except GitHubAPIError as exc:
            if exc.status_code != 422 or attempt == retry_limit:
                raise
            candidate = f"{base_name}-{uuid4().hex[:REPOSITORY_NAME_SUFFIX_LENGTH]}"
            logger.warning(
                "Repository name conflict; retrying with a new name",
                extra={"event": "project_creator.repository_name_conflict", "candidate": candidate},
            )

    raise GitHubAPIError("Unable to create a unique repository name")


def _avoid_local_duplicates(base_name: str, existing_names: set[str]) -> str:
    if base_name not in existing_names:
        return base_name
    return f"{base_name}-{uuid4().hex[:REPOSITORY_NAME_SUFFIX_LENGTH]}"


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:MAX_REPOSITORY_NAME_LENGTH].strip("-") or (
        f"generated-project-{uuid4().hex[:REPOSITORY_NAME_SUFFIX_LENGTH]}"
    )
