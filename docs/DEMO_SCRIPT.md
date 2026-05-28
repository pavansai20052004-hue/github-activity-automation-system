# Demo Video Script

Target length: 3 to 5 minutes.

## Opening

Hello, this is my GitHub Activity Automation System assessment submission. The project is a Python-based automation tool that includes two agents: a Daily Commit Agent and a Project Creator Agent.

The focus of my implementation is not only making GitHub API calls, but making the automation safe, configurable, repeatable, and easy for another engineer to operate.

## Project Overview

The repository contains three command-line entry points:

```bash
python daily_commit.py
python project_creator.py
python validate_config.py
```

The Daily Commit Agent selects an eligible owned repository and writes one to three activity commits to a configured tracking file. It avoids targeting the same repository as the previous run when possible.

The Project Creator Agent creates a new GitHub repository and seeds it with starter files such as a README, `.gitignore`, and source code. It supports both Python and JavaScript templates.

## Configuration

All meaningful settings are controlled by `config.json`. That includes commit counts, commit messages, target file path, language options, scheduling frequency, GitHub API settings, retry behavior, and kill switch settings.

Secrets are not stored in the repository. The GitHub token is loaded from `GITHUB_TOKEN`, either from the shell environment or from a local `.env` file that is ignored by Git.

## Safety Features

The first safety layer is idempotency. The Daily Commit Agent records the last successful run date, so running it twice on the same day is a no-op unless `--force` is used.

The second safety layer is a kill switch. Setting `kill_switch` to `true`, or creating the configured stop file, causes both agents to exit before making API calls.

The third safety layer is the runtime lock. This prevents two scheduled runs from overlapping and writing duplicate state or duplicate GitHub changes.

The fourth safety layer is dry-run mode. Reviewers can run:

```bash
python daily_commit.py --dry-run
python project_creator.py --dry-run --language python
```

Dry-run mode plans the work but skips GitHub writes and state mutations.

## GitHub API Integration

The project uses GitHub REST API v3 directly with `requests`.

The Daily Commit Agent uses repository listing and file content endpoints. The Project Creator Agent uses the repository creation endpoint and the file contents endpoint to seed starter files.

The client has retry and backoff logic for transient failures, server errors, rate-limit-style responses, and network issues.

## Persistence

State is stored in a local JSON file under the `state` directory. I chose JSON because the assessment state is small, easy to inspect, and does not require a database service.

The state tracks the last daily run date, last selected repository, last project creation date, and the list of generated project names.

## Validation

Before running the agents, the config can be checked with:

```bash
python validate_config.py
```

The test suite covers repository selection, idempotency, interval logic, config parsing, runtime locking, state persistence, and GitHub retry behavior.

The project also includes a GitHub Actions workflow that validates config and runs tests on every push and pull request.

## Closing

My main design decision was to treat this like a small production automation tool rather than a one-off script. That is why the solution includes config validation, structured logs, local durable state, dry-run mode, runtime locking, retry handling, and focused tests.

The repository is public and ready for review.

