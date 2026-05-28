from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _empty_state() -> dict[str, Any]:
    return {
        "daily_commit": {
            "last_run_date": None,
            "last_repository": None,
        },
        "project_creator": {
            "last_run_date": None,
            "created_projects": [],
        },
    }


class AutomationState:
    def __init__(self, path: Path, data: dict[str, Any] | None = None) -> None:
        self.path = path
        self.data = _merge_state(data or {})

    @classmethod
    def load(cls, path: Path) -> "AutomationState":
        if not path.exists():
            return cls(path)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
        return cls(path, loaded)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.path)

    def should_run_daily(self, today: date, force: bool = False) -> bool:
        if force:
            return True
        return self.data["daily_commit"]["last_run_date"] != today.isoformat()

    def mark_daily_run(self, today: date, repository_name: str) -> None:
        self.data["daily_commit"]["last_run_date"] = today.isoformat()
        self.data["daily_commit"]["last_repository"] = repository_name

    @property
    def last_daily_repository(self) -> str | None:
        value = self.data["daily_commit"].get("last_repository")
        return value if isinstance(value, str) else None

    def should_create_project(self, today: date, frequency_days: int, force: bool = False) -> bool:
        if force:
            return True

        last_run = self.data["project_creator"].get("last_run_date")
        if not last_run:
            return True

        try:
            last_run_date = date.fromisoformat(last_run)
        except ValueError:
            return True

        return today >= last_run_date + timedelta(days=frequency_days)

    def record_created_project(self, name: str, url: str, language: str) -> None:
        self.data["project_creator"]["last_run_date"] = date.today().isoformat()
        self.data["project_creator"]["created_projects"].append(
            {
                "name": name,
                "url": url,
                "language": language,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def created_project_names(self) -> set[str]:
        projects = self.data["project_creator"].get("created_projects", [])
        return {project["name"] for project in projects if isinstance(project, dict) and "name" in project}


def _merge_state(loaded: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(_empty_state())
    for section, defaults in merged.items():
        loaded_section = loaded.get(section)
        if isinstance(loaded_section, dict):
            defaults.update(loaded_section)
    if not isinstance(merged["project_creator"].get("created_projects"), list):
        merged["project_creator"]["created_projects"] = []
    return merged

