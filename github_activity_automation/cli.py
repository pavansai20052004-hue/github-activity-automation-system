from __future__ import annotations

import argparse
from collections.abc import Sequence

from .daily_commit_agent import run_daily_commit
from .project_creator_agent import run_project_creator


def daily_commit_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Daily Commit Agent.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--force", action="store_true", help="Bypass the once-per-day idempotency guard.")
    args = parser.parse_args(argv)
    return run_daily_commit(config_path=args.config, force=args.force)


def project_creator_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Project Creator Agent.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--force", action="store_true", help="Bypass the configured project creation interval.")
    parser.add_argument("--language", help="Project language to generate, such as python or javascript.")
    args = parser.parse_args(argv)
    return run_project_creator(config_path=args.config, force=args.force, language=args.language)

