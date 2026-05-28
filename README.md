# GitHub Activity Automation System

A configurable Python automation system that keeps GitHub activity moving in a controlled way. It includes a Daily Commit Agent that appends small activity entries to one owned repository per day, and a Project Creator Agent that creates starter repositories with generated project structure.

The project is built around safety: no hardcoded secrets, a config-driven kill switch, local persistent state for idempotency, dry-run support, scheduler lock protection, structured logs, and clear failure handling around GitHub API calls.

## Assessment Materials

- [Engineering approach](docs/APPROACH.md)
- [Architecture notes](docs/architecture.md)
- [Demo video script](docs/DEMO_SCRIPT.md)
- [Demo video](docs/demo/github_activity_automation_demo.mp4)
- [Submission notes](docs/SUBMISSION_NOTES.md)

## Prerequisites

- Python 3.10 or newer
- Git 2.30 or newer
- A GitHub account
- A GitHub Personal Access Token with the `repo` scope
- Optional: a Hugging Face token for external project idea generation

## Setup

```powershell
git clone https://github.com/pavansai20052004-hue/github-activity-automation-system.git
cd github-activity-automation-system

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## API Key Setup

1. Open GitHub and go to `Settings > Developer settings > Personal access tokens`.
2. Create a classic token.
3. Select the `repo` scope. Do not select `delete_repo`; this project does not delete repositories.
4. Copy the token into `.env`:

```env
GITHUB_TOKEN=ghp_replace_this_with_your_token
```

For optional external project ideas, add:

```env
HUGGINGFACE_API_TOKEN=hf_replace_this_if_you_have_one
```

`.env` is ignored by Git and must never be committed.

## Running The Agents

Run the Daily Commit Agent:

```bash
python daily_commit.py
```

Preview the selected repository and planned commits without writing anything:

```bash
python daily_commit.py --dry-run
```

Force a test run even if today already ran:

```bash
python daily_commit.py --force
```

Run the Project Creator Agent:

```bash
python project_creator.py
```

Choose a language explicitly:

```bash
python project_creator.py --language javascript
```

Preview the repository name and starter files without creating anything:

```bash
python project_creator.py --dry-run --language python
```

Force project creation even if the interval has not elapsed:

```bash
python project_creator.py --force --language python
```

Validate configuration before scheduling:

```bash
python validate_config.py
python validate_config.py --check-env
```

## Configuration Guide

All meaningful settings live in `config.json`.

| Key | Default | Description |
| --- | --- | --- |
| `kill_switch` | `false` | When `true`, both agents exit before making API calls. |
| `kill_switch_file` | `STOP_AGENTS` | If this file exists, both agents stop before API calls. |
| `state_file` | `state/automation_state.json` | Local JSON state used for idempotency and duplicate prevention. |
| `log_file` | `logs/automation.log` | Structured JSON log file path. |
| `log_level` | `INFO` | Logging threshold. |
| `runtime.lock_file` | `state/automation.lock` | Exclusive lock file that prevents overlapping scheduled runs. |
| `runtime.lock_stale_after_minutes` | `60` | Age after which an abandoned lock can be replaced. |
| `secrets.github_token_env` | `GITHUB_TOKEN` | Environment variable that stores the GitHub token. |
| `secrets.huggingface_token_env` | `HUGGINGFACE_API_TOKEN` | Environment variable for optional idea generation. |
| `github.api_base_url` | `https://api.github.com` | GitHub REST API v3 base URL. |
| `github.request_timeout_seconds` | `20` | Timeout for outbound API requests. |
| `github.max_retries` | `3` | Retry count for transient API, network, and rate-limit failures. |
| `github.retry_backoff_seconds` | `2` | Base exponential backoff delay between retries. |
| `daily_commit.target_file` | `.contributions/activity.log` | File updated in the selected repository. |
| `daily_commit.commit_count.min` | `1` | Minimum commits per successful daily run. |
| `daily_commit.commit_count.max` | `3` | Maximum commits per successful daily run. |
| `daily_commit.commit_messages` | See config | Pool of distinct commit messages. Must contain at least `max` values. |
| `daily_commit.excluded_repositories` | Current project repo | Repositories never selected for activity commits. |
| `project_creator.frequency_days` | `7` | Minimum days between project creation runs. |
| `project_creator.visibility` | `public` | Creates public repositories by default. Use `private` if needed. |
| `project_creator.name_prefix` | `automation-lab` | Prefix added to generated repository names. |
| `project_creator.languages` | `["python", "javascript"]` | Languages the creator may generate. |
| `project_creator.default_language` | `python` | Language used when `--language` is omitted. |
| `project_creator.name_retry_limit` | `5` | Number of alternate names to try if GitHub reports a conflict. |
| `project_creator.external_idea_provider.enabled` | `true` | Attempts external idea generation when a token is available. |
| `project_creator.external_idea_provider.provider` | `huggingface` | Currently supported external provider. |
| `project_creator.external_idea_provider.model` | `mistralai/Mixtral-8x7B-Instruct-v0.1` | Hugging Face model endpoint name. |

## Kill Switch

Use either kill switch option when you need to pause automation immediately.

Option 1: edit `config.json`:

```json
"kill_switch": true
```

Option 2: create a file named `STOP_AGENTS` in the project root:

```bash
touch STOP_AGENTS
```

Both agents check the kill switch before reading credentials or calling GitHub.

## Scheduler Safety

Both agents use the same exclusive lock file before they read or write state. This prevents two scheduled runs from racing each other and accidentally creating duplicate activity. If a previous process exits unexpectedly, the lock is considered stale after `runtime.lock_stale_after_minutes`.

## Scheduling

Cron example for Linux or macOS:

```cron
15 9 * * * cd /path/to/github-activity-automation-system && /path/to/.venv/bin/python daily_commit.py
30 9 */7 * * cd /path/to/github-activity-automation-system && /path/to/.venv/bin/python project_creator.py
```

Windows Task Scheduler example:

1. Open Task Scheduler.
2. Create a basic task.
3. Trigger: daily.
4. Action: start a program.
5. Program: `C:\path\to\github-activity-automation-system\.venv\Scripts\python.exe`
6. Arguments: `daily_commit.py`
7. Start in: `C:\path\to\github-activity-automation-system`

Create a second task for `project_creator.py` if desired.

## Project Structure

```text
.
|-- daily_commit.py                         # CLI wrapper for the Daily Commit Agent
|-- project_creator.py                      # CLI wrapper for the Project Creator Agent
|-- validate_config.py                      # Preflight config and environment validator
|-- config.json                             # Single source of configurable behavior
|-- requirements.txt                        # Pinned Python dependencies
|-- scripts/
|   `-- generate_demo_video.py              # Optional helper used to render the demo MP4
|-- github_activity_automation/
|   |-- cli.py                              # Argument parsing entry points
|   |-- config.py                           # Config loading and validation
|   |-- content_provider.py                 # External and fallback project ideas
|   |-- daily_commit_agent.py               # Daily Commit Agent orchestration
|   |-- exceptions.py                       # Domain exceptions
|   |-- github_client.py                    # GitHub REST API v3 client
|   |-- logging_setup.py                    # JSON logging to stdout and file
|   |-- project_creator_agent.py            # Project Creator Agent orchestration
|   |-- project_templates.py                # Python and JavaScript starter files
|   |-- repository_selector.py              # Random repo selection logic
|   |-- runtime_lock.py                     # Cross-platform scheduler lock
|   `-- state.py                            # Local JSON state persistence
|-- tests/
|   |-- test_config.py                      # Config validation coverage
|   |-- test_github_client.py               # Retry behavior coverage
|   |-- test_repository_selector.py         # Repo avoidance behavior
|   |-- test_runtime_lock.py                # Lock acquisition and stale-lock coverage
|   `-- test_state.py                       # Idempotency and interval behavior
`-- docs/
    |-- APPROACH.md                         # Detailed assessment approach
    |-- DEMO_SCRIPT.md                      # Demo video narration and flow
    |-- SUBMISSION_NOTES.md                 # Email-ready submission note
    |-- architecture.md                     # Design notes and trade-offs
    `-- demo/
        `-- github_activity_automation_demo.mp4
```

## Troubleshooting

`Missing GitHub token`
: Add `GITHUB_TOKEN` to `.env`, then run the command again from the project root.

`GitHub API error 401`
: The token is invalid, expired, or missing the required `repo` scope.

`Daily agent says no eligible repositories`
: The authenticated account may only have forks, archived repositories, or repositories excluded by `config.json`.

`Project creator says interval has not elapsed`
: This is expected idempotency behavior. Use `--force` for testing.

`Another automation run is already active`
: A scheduler overlap was blocked by the runtime lock. Wait for the active run to finish, or remove the lock only if you are sure no process is running.

`Hugging Face request failed`
: The creator logs the issue and falls back to built-in project ideas automatically.

## Design Decisions

- State is stored in a local JSON file because the assessment needs durable idempotency without requiring a database server.
- The GitHub integration uses raw REST calls through `requests` to keep the external surface small and transparent.
- The Project Creator creates files through the GitHub Contents API so the system does not need shelling out to `git` for generated repositories.
- The current repository is excluded from Daily Commit Agent selection by default to avoid the automation modifying its own source repo.
- Dry runs intentionally perform read-only planning but skip writes and state changes, which makes scheduler testing safer.
- A lock file is used instead of a long-running daemon or database lock because the project is designed for simple cron and Task Scheduler environments.

## Validation

Run tests with:

```bash
pytest
```

The repository also includes a GitHub Actions workflow that runs the same test suite on every push and pull request.
