from datetime import date

from github_activity_automation.state import AutomationState


def test_daily_commit_idempotency_blocks_second_run_same_day(tmp_path):
    state = AutomationState(tmp_path / "state.json")
    today = date(2026, 5, 28)

    assert state.should_run_daily(today)
    state.mark_daily_run(today, "demo-repo")

    assert not state.should_run_daily(today)
    assert state.should_run_daily(today, force=True)


def test_project_creator_interval_allows_run_after_frequency(tmp_path):
    state = AutomationState(tmp_path / "state.json")
    state.data["project_creator"]["last_run_date"] = "2026-05-20"

    assert not state.should_create_project(date(2026, 5, 26), frequency_days=7)
    assert state.should_create_project(date(2026, 5, 27), frequency_days=7)


def test_state_round_trips_created_projects(tmp_path):
    path = tmp_path / "state.json"
    state = AutomationState(path)
    state.record_created_project("demo-project", "https://github.com/user/demo-project", "python")
    state.save()

    loaded = AutomationState.load(path)

    assert "demo-project" in loaded.created_project_names()

