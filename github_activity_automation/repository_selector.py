from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from .exceptions import RepositorySelectionError


def select_repository(
    repositories: Sequence[Mapping[str, Any]],
    last_repository: str | None,
    excluded_repositories: Sequence[str],
    rng: random.Random | random.SystemRandom | None = None,
) -> Mapping[str, Any]:
    """Select an eligible repository while avoiding the previous target when possible."""

    eligible = [
        repository
        for repository in repositories
        if repository.get("name") not in set(excluded_repositories)
        and repository.get("full_name") not in set(excluded_repositories)
    ]
    if not eligible:
        raise RepositorySelectionError("No eligible repositories are available")

    candidates = eligible
    if last_repository and len(eligible) > 1:
        avoided = [
            repository
            for repository in eligible
            if repository.get("name") != last_repository and repository.get("full_name") != last_repository
        ]
        if avoided:
            candidates = avoided

    chooser = rng or random.SystemRandom()
    return chooser.choice(list(candidates))

