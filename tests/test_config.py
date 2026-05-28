from github_activity_automation.config import load_config


def test_load_config_parses_runtime_and_retry_settings():
    config = load_config("config.json")

    assert config.runtime.lock_file.name == "automation.lock"
    assert config.runtime.lock_stale_after_seconds == 3600
    assert config.github.max_retries == 3
    assert config.github.retry_backoff_seconds == 2

