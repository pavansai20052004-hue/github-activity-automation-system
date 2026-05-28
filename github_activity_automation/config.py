from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from dotenv import load_dotenv

from .exceptions import ConfigError, MissingCredentialError


@dataclass(frozen=True)
class SecretSettings:
    github_token_env: str
    huggingface_token_env: str


@dataclass(frozen=True)
class RuntimeSettings:
    lock_file: Path
    lock_stale_after_seconds: int


@dataclass(frozen=True)
class GitHubSettings:
    api_base_url: str
    request_timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float


@dataclass(frozen=True)
class DailyCommitSettings:
    target_file: str
    min_commits: int
    max_commits: int
    commit_messages: tuple[str, ...]
    excluded_repositories: tuple[str, ...]


@dataclass(frozen=True)
class ExternalIdeaProviderSettings:
    enabled: bool
    provider: str
    model: str


@dataclass(frozen=True)
class ProjectCreatorSettings:
    frequency_days: int
    visibility: str
    name_prefix: str
    languages: tuple[str, ...]
    default_language: str
    name_retry_limit: int
    external_idea_provider: ExternalIdeaProviderSettings


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    kill_switch: bool
    kill_switch_file: Path
    state_file: Path
    log_file: Path
    log_level: str
    runtime: RuntimeSettings
    secrets: SecretSettings
    github: GitHubSettings
    daily_commit: DailyCommitSettings
    project_creator: ProjectCreatorSettings

    @property
    def kill_switch_active(self) -> bool:
        return self.kill_switch or self.kill_switch_file.exists()


def load_config(config_path: str | Path = "config.json") -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    load_dotenv(path.parent / ".env", override=False)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    config_dir = path.parent
    runtime = _load_runtime(raw, config_dir)
    secrets = _load_secrets(raw)
    github = _load_github(raw)
    daily_commit = _load_daily_commit(raw)
    project_creator = _load_project_creator(raw)

    return AppConfig(
        config_path=path,
        kill_switch=_require_bool(raw, "kill_switch"),
        kill_switch_file=_resolve_path(config_dir, _require_str(raw, "kill_switch_file")),
        state_file=_resolve_path(config_dir, _require_str(raw, "state_file")),
        log_file=_resolve_path(config_dir, _require_str(raw, "log_file")),
        log_level=_require_str(raw, "log_level").upper(),
        runtime=runtime,
        secrets=secrets,
        github=github,
        daily_commit=daily_commit,
        project_creator=project_creator,
    )


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingCredentialError(f"Required environment variable is missing: {name}")
    return value


def _load_runtime(raw: dict[str, Any], config_dir: Path) -> RuntimeSettings:
    section = _require_dict(raw, "runtime")
    stale_minutes = _require_int(section, "lock_stale_after_minutes")
    if stale_minutes < 1:
        raise ConfigError("runtime.lock_stale_after_minutes must be at least 1")
    return RuntimeSettings(
        lock_file=_resolve_path(config_dir, _require_str(section, "lock_file")),
        lock_stale_after_seconds=stale_minutes * 60,
    )


def _load_secrets(raw: dict[str, Any]) -> SecretSettings:
    section = _require_dict(raw, "secrets")
    return SecretSettings(
        github_token_env=_require_str(section, "github_token_env"),
        huggingface_token_env=_require_str(section, "huggingface_token_env"),
    )


def _load_github(raw: dict[str, Any]) -> GitHubSettings:
    section = _require_dict(raw, "github")
    timeout = _require_number(section, "request_timeout_seconds")
    if timeout <= 0:
        raise ConfigError("github.request_timeout_seconds must be greater than 0")
    max_retries = _require_int(section, "max_retries")
    if max_retries < 0:
        raise ConfigError("github.max_retries must be 0 or greater")
    retry_backoff = _require_number(section, "retry_backoff_seconds")
    if retry_backoff < 0:
        raise ConfigError("github.retry_backoff_seconds must be 0 or greater")
    return GitHubSettings(
        api_base_url=_require_str(section, "api_base_url").rstrip("/"),
        request_timeout_seconds=timeout,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff,
    )


def _load_daily_commit(raw: dict[str, Any]) -> DailyCommitSettings:
    section = _require_dict(raw, "daily_commit")
    commit_count = _require_dict(section, "commit_count")
    min_commits = _require_int(commit_count, "min")
    max_commits = _require_int(commit_count, "max")
    if min_commits < 1:
        raise ConfigError("daily_commit.commit_count.min must be at least 1")
    if max_commits < min_commits:
        raise ConfigError("daily_commit.commit_count.max must be >= min")

    messages = tuple(_require_str_list(section, "commit_messages"))
    if len(set(messages)) < max_commits:
        raise ConfigError("daily_commit.commit_messages must contain at least max distinct messages")

    target_file = _require_repo_relative_path(section, "target_file")
    excluded = tuple(_require_str_list(section, "excluded_repositories"))
    return DailyCommitSettings(
        target_file=target_file,
        min_commits=min_commits,
        max_commits=max_commits,
        commit_messages=messages,
        excluded_repositories=excluded,
    )


def _load_project_creator(raw: dict[str, Any]) -> ProjectCreatorSettings:
    section = _require_dict(raw, "project_creator")
    frequency_days = _require_int(section, "frequency_days")
    if frequency_days < 1:
        raise ConfigError("project_creator.frequency_days must be at least 1")

    visibility = _require_str(section, "visibility").lower()
    if visibility not in {"public", "private"}:
        raise ConfigError("project_creator.visibility must be either public or private")

    languages = tuple(language.lower() for language in _require_str_list(section, "languages"))
    if not languages:
        raise ConfigError("project_creator.languages must not be empty")

    default_language = _require_str(section, "default_language").lower()
    if default_language not in languages:
        raise ConfigError("project_creator.default_language must be listed in project_creator.languages")

    retry_limit = _require_int(section, "name_retry_limit")
    if retry_limit < 1:
        raise ConfigError("project_creator.name_retry_limit must be at least 1")

    provider = _require_dict(section, "external_idea_provider")
    external = ExternalIdeaProviderSettings(
        enabled=_require_bool(provider, "enabled"),
        provider=_require_str(provider, "provider").lower(),
        model=_require_str(provider, "model"),
    )
    if external.provider != "huggingface":
        raise ConfigError("Only the huggingface external idea provider is currently supported")

    return ProjectCreatorSettings(
        frequency_days=frequency_days,
        visibility=visibility,
        name_prefix=_require_str(section, "name_prefix"),
        languages=languages,
        default_language=default_language,
        name_retry_limit=retry_limit,
        external_idea_provider=external,
    )


def _resolve_path(config_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_dir / path


def _require_dict(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Config key must be an object: {key}")
    return value


def _require_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config key must be a non-empty string: {key}")
    return value.strip()


def _require_bool(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"Config key must be a boolean: {key}")
    return value


def _require_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int):
        raise ConfigError(f"Config key must be an integer: {key}")
    return value


def _require_number(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, (int, float)):
        raise ConfigError(f"Config key must be a number: {key}")
    return float(value)


def _require_str_list(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"Config key must be a list of non-empty strings: {key}")
    return [item.strip() for item in value]


def _require_repo_relative_path(raw: dict[str, Any], key: str) -> str:
    value = _require_str(raw, key).replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigError(f"Config key must be a repository-relative path: {key}")
    return str(path)
