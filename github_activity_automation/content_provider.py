from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass

import requests

from .config import ProjectCreatorSettings, SecretSettings


@dataclass(frozen=True)
class ProjectIdea:
    title: str
    description: str


BUILT_IN_IDEAS = (
    ProjectIdea("CLI Habit Tracker", "A small command-line app for recording habits and streaks."),
    ProjectIdea("Markdown Link Auditor", "A utility that scans Markdown files and reports broken links."),
    ProjectIdea("JSON Config Inspector", "A tool that validates config files and prints actionable diagnostics."),
    ProjectIdea("Local Notes Search", "A lightweight script for indexing and searching local notes."),
    ProjectIdea("API Health Check Runner", "A tiny health-check runner for monitoring HTTP endpoints."),
)

MAX_GENERATED_IDEA_TOKENS = 80
MAX_IDEA_TITLE_CHARS = 80
MAX_IDEA_DESCRIPTION_CHARS = 240


def get_project_idea(
    settings: ProjectCreatorSettings,
    secrets: SecretSettings,
    timeout_seconds: float,
    existing_names: set[str],
    logger: logging.Logger,
) -> ProjectIdea:
    if settings.external_idea_provider.enabled:
        idea = _try_huggingface(settings, secrets, timeout_seconds, logger)
        if idea:
            return idea

    available = [
        idea
        for idea in BUILT_IN_IDEAS
        if _slugify_for_compare(settings.name_prefix, idea.title) not in existing_names
    ]
    chosen = random.SystemRandom().choice(available or list(BUILT_IN_IDEAS))
    logger.info(
        "Using built-in project idea",
        extra={"event": "project_creator.idea.fallback", "idea_title": chosen.title},
    )
    return chosen


def _try_huggingface(
    settings: ProjectCreatorSettings,
    secrets: SecretSettings,
    timeout_seconds: float,
    logger: logging.Logger,
) -> ProjectIdea | None:
    token = os.getenv(secrets.huggingface_token_env)
    if not token:
        logger.info(
            "Hugging Face token not configured; falling back to built-in ideas",
            extra={"event": "project_creator.idea.no_external_token"},
        )
        return None

    prompt = (
        "Generate one practical beginner-friendly software project idea. "
        "Return exactly two lines: Name: <short name> and Description: <one sentence>."
    )
    url = f"https://api-inference.huggingface.co/models/{settings.external_idea_provider.model}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": MAX_GENERATED_IDEA_TOKENS, "temperature": 0.7, "return_full_text": False},
        "options": {"wait_for_model": False},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "External idea provider failed; falling back to built-in ideas",
            extra={"event": "project_creator.idea.external_failed", "error": str(exc)},
        )
        return None

    text = _extract_generated_text(data)
    idea = _parse_idea_text(text)
    if idea:
        logger.info(
            "Using external project idea",
            extra={"event": "project_creator.idea.external", "idea_title": idea.title},
        )
    return idea


def _extract_generated_text(data: object) -> str:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return str(data[0].get("generated_text", ""))
    if isinstance(data, dict):
        return str(data.get("generated_text", ""))
    return ""


def _parse_idea_text(text: str) -> ProjectIdea | None:
    name = None
    description = None
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.lower().startswith("name:"):
            name = cleaned.split(":", 1)[1].strip()
        elif cleaned.lower().startswith("description:"):
            description = cleaned.split(":", 1)[1].strip()
    if name and description:
        return ProjectIdea(title=name[:MAX_IDEA_TITLE_CHARS], description=description[:MAX_IDEA_DESCRIPTION_CHARS])
    return None


def _slugify_for_compare(prefix: str, title: str) -> str:
    return "-".join(f"{prefix}-{title}".lower().replace("_", "-").split())
