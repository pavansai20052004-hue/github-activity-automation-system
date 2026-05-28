from __future__ import annotations

import argparse
from collections.abc import Sequence

from .config import load_config, require_env
from .daily_commit_agent import run_daily_commit
from .exceptions import AutomationError
from .project_creator_agent import run_project_creator


def daily_commit_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Daily Commit Agent.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--force", action="store_true", help="Bypass the once-per-day idempotency guard.")
    parser.add_argument("--dry-run", action="store_true", help="Plan the run without writing commits or state.")
    args = parser.parse_args(argv)
    return run_daily_commit(config_path=args.config, force=args.force, dry_run=args.dry_run)


def project_creator_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Project Creator Agent.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--force", action="store_true", help="Bypass the configured project creation interval.")
    parser.add_argument("--language", help="Project language to generate, such as python or javascript.")
    parser.add_argument("--dry-run", action="store_true", help="Plan the run without creating a repo or writing state.")
    args = parser.parse_args(argv)
    return run_project_creator(
        config_path=args.config,
        force=args.force,
        language=args.language,
        dry_run=args.dry_run,
    )


def validate_config_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate configuration and optional environment variables.")
    parser.add_argument("--config", default="config.json", help="Path to config.json.")
    parser.add_argument("--check-env", action="store_true", help="Also verify required environment variables.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.check_env:
            require_env(config.secrets.github_token_env)
    except AutomationError as exc:
        print(f"Config validation failed: {exc}")
        return 1

    print(f"Config valid: {config.config_path}")
    if args.check_env:
        print("Required environment variables are present.")
    return 0
