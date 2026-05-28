import logging

from github_activity_automation.github_client import GitHubClient


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.content = b"{}"
        self.text = "{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers = {}

    def request(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def test_github_client_retries_transient_server_error():
    client = GitHubClient(
        token="token",
        api_base_url="https://api.github.test",
        timeout_seconds=1,
        max_retries=1,
        retry_backoff_seconds=0,
        logger=logging.getLogger("test"),
    )
    session = FakeSession(
        [
            FakeResponse(500, {"message": "temporary"}),
            FakeResponse(200, {"login": "pavansai20052004-hue"}),
        ]
    )
    client.session = session

    result = client.get_authenticated_user()

    assert result == {"login": "pavansai20052004-hue"}
    assert session.calls == 2

