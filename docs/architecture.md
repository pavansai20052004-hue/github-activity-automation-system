# Architecture Notes

## Components

The system is split into small modules so the behavior is easy to test and reason about.

- `config.py` loads and validates the single JSON config file.
- `github_client.py` wraps GitHub REST API v3 calls and converts network/API failures into domain exceptions.
- `state.py` owns durable local JSON state and idempotency decisions.
- `runtime_lock.py` prevents overlapping scheduler runs from touching state or GitHub at the same time.
- `repository_selector.py` contains the previous-repository avoidance logic.
- `daily_commit_agent.py` orchestrates the daily commit workflow.
- `project_creator_agent.py` orchestrates new repository creation and file seeding.
- `content_provider.py` optionally calls Hugging Face and falls back to built-in ideas.
- `project_templates.py` contains language-specific starter file templates.

## State Choice

State is persisted in JSON instead of SQLite because the required data is small: last daily run date, last selected repository, project creation date, and created project names. JSON keeps setup simple while still surviving process restarts, which is the important requirement for idempotency.

Writes are atomic: the state file is written to a temporary path and then replaced.

## Safety Model

Both agents check the config kill switch and the kill-switch file before reading credentials or making API calls. The `.env` file is excluded by `.gitignore`, and token names are configurable through `config.json`.

Both agents also acquire an exclusive lock file before reading or writing state. This protects cron and Task Scheduler setups from overlapping runs. Stale locks are replaced only after the configured age.

Dry-run mode performs planning and read-only API calls, then exits before any GitHub write or state mutation.

## Error Handling

Expected failures raise `AutomationError` subclasses and are logged as structured JSON. Unexpected failures are caught at the agent boundary and logged with stack traces. The CLI returns a non-zero exit code for failures so schedulers and CI jobs can detect problems.

The GitHub client retries transient server errors, network failures, and rate-limit responses using configurable exponential backoff. It respects `Retry-After` when GitHub provides one.

## GitHub API Usage

The implementation uses raw REST calls through `requests` for transparency and portability. The Daily Commit Agent uses:

- `GET /user/repos`
- `GET /repos/{owner}/{repo}/contents/{path}`
- `PUT /repos/{owner}/{repo}/contents/{path}`

The Project Creator Agent uses:

- `GET /user`
- `POST /user/repos`
- `PUT /repos/{owner}/{repo}/contents/{path}`

## Trade-offs

- Generated project repositories are seeded file by file through the Contents API. This creates simple, auditable commits, but it is less efficient than creating a full Git tree in one API call.
- The Daily Commit Agent records activity in a tracking file instead of changing application code. That keeps automated changes isolated and reversible.
- External idea generation is optional and best-effort. The fallback list ensures project creation still works when the external API is unavailable.
- The lock is file-based rather than database-backed to preserve the project's no-service local setup.
