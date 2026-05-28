# Engineering Approach

## Problem Understanding

The assessment asks for a GitHub Activity Automation System with two agents:

- A Daily Commit Agent that safely creates small activity commits in existing repositories.
- A Project Creator Agent that periodically creates new starter repositories.

The important engineering challenge is not just making GitHub API calls. The system must be safe to run repeatedly, configurable without code changes, resilient to external API failures, and understandable enough for another engineer to clone and operate quickly.

## Goals

- Keep all meaningful behavior in `config.json`.
- Load secrets only from environment variables or `.env`.
- Avoid hardcoded tokens, usernames, intervals, commit counts, file names, or message pools.
- Persist state locally so repeated runs are idempotent.
- Use GitHub REST API v3 directly through `requests`.
- Fail clearly with structured logs instead of crashing silently.
- Make scheduled runs safe with a kill switch, dry-run mode, and runtime locking.
- Provide tests for the highest-risk logic.

## Architecture

The project is organized as a small Python package with thin CLI wrappers at the root:

```text
daily_commit.py       -> Daily Commit Agent entry point
project_creator.py    -> Project Creator Agent entry point
validate_config.py    -> Preflight config/environment validator
github_activity_automation/
  config.py           -> Config parsing and validation
  github_client.py    -> GitHub REST API wrapper
  state.py            -> Local persistent JSON state
  runtime_lock.py     -> Scheduler overlap protection
  repository_selector.py
  daily_commit_agent.py
  project_creator_agent.py
  content_provider.py
  project_templates.py
```

This keeps agent orchestration separate from lower-level concerns like config, state, logging, GitHub API behavior, and repository selection.

## Daily Commit Agent Flow

1. Load and validate `config.json`.
2. Configure structured logging to stdout and `logs/automation.log`.
3. Check the config kill switch and kill-switch file.
4. Acquire the runtime lock to prevent overlapping scheduled runs.
5. Load local state from `state/automation_state.json`.
6. Stop as a no-op if the agent already ran today, unless `--force` is used.
7. Load the GitHub token from the configured environment variable.
8. Fetch owned repositories and filter out forks and archived repositories.
9. Select a random eligible repository while avoiding the previous target when possible.
10. Choose 1 to 3 distinct commit messages from config.
11. If `--dry-run` is enabled, log the plan and stop before writing anything.
12. Read or create the configured activity file.
13. Write the configured number of commits through the GitHub Contents API.
14. Save last run date and last targeted repository in local state.

## Project Creator Agent Flow

1. Load config, logging, kill switch, runtime lock, and state.
2. Stop as a no-op if the configured interval has not elapsed, unless `--force` is used.
3. Validate the requested language against configured and implemented languages.
4. Load the GitHub token from the environment.
5. Fetch the authenticated GitHub username.
6. Try to get an external project idea from Hugging Face if configured and token is available.
7. Fall back to a built-in project idea list if the external provider is unavailable.
8. Generate a repository name and avoid locally known duplicates.
9. If `--dry-run` is enabled, log the repository name and files that would be created.
10. Create the GitHub repository.
11. Seed starter files such as `README.md`, `.gitignore`, and source files.
12. Save the created project to local state.

## Safety Decisions

### Idempotency

The Daily Commit Agent records `last_run_date` and exits as a no-op when run again on the same day. The Project Creator Agent records `last_run_date` and respects the configured interval.

### Runtime Lock

Scheduled automation can overlap if a previous run is slow or a scheduler is misconfigured. A cross-platform lock file prevents two runs from touching GitHub or state at the same time. Stale locks are replaced only after the configured age.

### Dry Run

Both agents support `--dry-run`. This lets reviewers and operators verify config, repository selection, language selection, and generated file plans without creating commits, repositories, or state changes.

### Kill Switch

The project supports two stop mechanisms:

- `kill_switch: true` in `config.json`
- A file named by `kill_switch_file`, defaulting to `STOP_AGENTS`

Both agents check the kill switch before making GitHub API calls.

### Secrets

Secrets are loaded from environment variables or `.env` through `python-dotenv`. `.env` is ignored by Git. `.env.example` documents required values without exposing real tokens.

## GitHub API Strategy

The implementation uses raw REST API calls instead of a large wrapper library. This keeps behavior explicit and easy to audit.

Key endpoints:

- `GET /user`
- `GET /user/repos`
- `GET /repos/{owner}/{repo}/contents/{path}`
- `PUT /repos/{owner}/{repo}/contents/{path}`
- `POST /user/repos`

The client retries transient failures such as network errors, `429`, `500`, `502`, `503`, `504`, and rate-limit-style `403` responses. Retry count and backoff are configured in `config.json`.

## Persistence Strategy

The system uses a local JSON file instead of SQLite because the state is small and simple:

- Last Daily Commit Agent date
- Last targeted repository
- Last Project Creator Agent date
- List of created project names

JSON is easy to inspect during assessment and requires no extra service setup. Writes are done through a temporary file and then replaced to reduce the risk of partial state writes.

## Testing Strategy

The tests target the highest-risk behavior:

- Repository selection avoids the previous repository when possible.
- Repository selection respects exclusions.
- Daily run idempotency blocks duplicate same-day runs.
- Project creation interval logic works.
- State persists created projects.
- Config parses runtime and retry settings.
- Runtime locks prevent overlap and recover stale locks.
- GitHub client retries transient failures.

Current validation:

```bash
python validate_config.py
python -m pytest -q
```

## Trade-offs

- The Project Creator Agent seeds files one by one through the Contents API. This is simple and auditable, though less efficient than creating a Git tree in one request.
- JSON state is intentionally lightweight. A database would be more appropriate only if the system needed multi-user state, remote execution, or analytics.
- External idea generation is optional. The fallback list is used by design so the system remains reliable without extra API tokens.
- The Daily Commit Agent writes to a dedicated activity file rather than changing application code, keeping automated commits isolated.

## Assessment Requirements Mapping

| Requirement | Implementation |
| --- | --- |
| GitHub REST API authentication | `GITHUB_TOKEN` loaded from environment or `.env` |
| Fetch non-forked, non-archived repositories | `GitHubClient.list_owned_repositories()` |
| Random repo selection with previous-target avoidance | `repository_selector.py` |
| 1 to 3 commits per run | Configured by `daily_commit.commit_count` |
| Configurable commit messages | `daily_commit.commit_messages` |
| Once-per-day idempotency | `AutomationState.should_run_daily()` |
| `--force` flag | Supported by both agent CLIs |
| Create public repos | `ProjectCreatorAgent` with `visibility: public` |
| README, `.gitignore`, starter source | `project_templates.py` |
| Two languages | Python and JavaScript templates |
| Optional external idea API with fallback | Hugging Face plus built-in ideas |
| Duplicate project prevention | Local created-project state and name retry |
| Config file for meaningful parameters | `config.json` |
| Kill switch | Config key and file-based switch |
| Structured logging | JSON logs to stdout and file |
| Graceful error handling | `AutomationError` boundary and logged failures |
| Tests bonus | 12 focused tests plus GitHub Actions |

