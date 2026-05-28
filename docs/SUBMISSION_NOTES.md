# Submission Notes

Repository link:

```text
https://github.com/pavansai20052004-hue/github-activity-automation-system
```

## Short Email Reply

```text
Hello,

Here is my assessment submission:
https://github.com/pavansai20052004-hue/github-activity-automation-system

I implemented a GitHub Activity Automation System with a Daily Commit Agent and a Project Creator Agent. The system uses GitHub REST API v3, config-driven behavior, local JSON state for idempotency, structured logging, retry/backoff handling, dry-run support, a kill switch, and runtime locking for scheduler safety. I chose JSON persistence because the required state is small and easy to inspect, while still surviving process restarts. I also included focused tests, GitHub Actions validation, an approach document, and a narrated demo video with embedded voice in the repository.

Thank you.
```

## Demo Links To Mention

- Approach document: `docs/APPROACH.md`
- Demo script: `docs/DEMO_SCRIPT.md`
- Narrated demo video: `docs/demo/github_activity_automation_narrated_demo.mp4`
- Architecture notes: `docs/architecture.md`

## Commands To Show During Live Demo

```bash
python validate_config.py
python daily_commit.py --help
python project_creator.py --help
python daily_commit.py --dry-run
python project_creator.py --dry-run --language python
python -m pytest -q
```

Note: the two `--dry-run` commands require a local `GITHUB_TOKEN` because they perform read-only planning against GitHub before skipping writes. The token should be placed in `.env` and must not be committed.
