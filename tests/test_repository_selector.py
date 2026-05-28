import random

import pytest

from github_activity_automation.exceptions import RepositorySelectionError
from github_activity_automation.repository_selector import select_repository


def test_select_repository_avoids_previous_repository_when_possible():
    repositories = [
        {"name": "alpha", "full_name": "user/alpha"},
        {"name": "beta", "full_name": "user/beta"},
    ]

    selected = select_repository(
        repositories,
        last_repository="alpha",
        excluded_repositories=[],
        rng=random.Random(0),
    )

    assert selected["name"] == "beta"


def test_select_repository_can_reuse_previous_when_it_is_the_only_choice():
    repositories = [{"name": "alpha", "full_name": "user/alpha"}]

    selected = select_repository(
        repositories,
        last_repository="alpha",
        excluded_repositories=[],
        rng=random.Random(0),
    )

    assert selected["name"] == "alpha"


def test_select_repository_respects_exclusions():
    repositories = [
        {"name": "alpha", "full_name": "user/alpha"},
        {"name": "beta", "full_name": "user/beta"},
    ]

    selected = select_repository(
        repositories,
        last_repository=None,
        excluded_repositories=["alpha"],
        rng=random.Random(0),
    )

    assert selected["name"] == "beta"


def test_select_repository_raises_when_no_eligible_repositories_exist():
    repositories = [{"name": "alpha", "full_name": "user/alpha"}]

    with pytest.raises(RepositorySelectionError):
        select_repository(
            repositories,
            last_repository=None,
            excluded_repositories=["alpha"],
            rng=random.Random(0),
        )

