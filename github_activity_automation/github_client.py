from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import requests

from .exceptions import GitHubAPIError


GITHUB_PAGE_SIZE = 100
ERROR_BODY_PREVIEW_CHARS = 500


@dataclass(frozen=True)
class GitHubFile:
    content: str
    sha: str | None


class GitHubClient:
    def __init__(self, token: str, api_base_url: str, timeout_seconds: float, logger: logging.Logger) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-activity-automation-system/1.0",
            }
        )

    def get_authenticated_user(self) -> dict[str, Any]:
        return self._request("GET", "/user")

    def list_owned_repositories(self) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        for page in self._paginate(
            "/user/repos",
            params={"affiliation": "owner", "sort": "updated", "direction": "desc"},
        ):
            for repository in page:
                if not repository.get("fork") and not repository.get("archived"):
                    repositories.append(repository)
        return repositories

    def get_file(self, repository_full_name: str, file_path: str) -> GitHubFile | None:
        try:
            payload = self._request("GET", f"/repos/{repository_full_name}/contents/{file_path}")
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return None
            raise

        encoded = payload.get("content", "")
        if payload.get("encoding") != "base64":
            raise GitHubAPIError(f"Unsupported content encoding for {file_path}")

        text = base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
        return GitHubFile(content=text, sha=payload.get("sha"))

    def put_file(
        self,
        repository_full_name: str,
        file_path: str,
        message: str,
        content: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        }
        if sha:
            body["sha"] = sha
        return self._request("PUT", f"/repos/{repository_full_name}/contents/{file_path}", json=body)

    def create_repository(self, name: str, description: str, private: bool) -> dict[str, Any]:
        body = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": False,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False,
        }
        return self._request("POST", "/user/repos", json=body)

    def _paginate(self, path: str, params: dict[str, Any]) -> list[list[dict[str, Any]]]:
        pages: list[list[dict[str, Any]]] = []
        page_number = 1
        while True:
            page_params = {**params, "per_page": GITHUB_PAGE_SIZE, "page": page_number}
            payload = self._request("GET", path, params=page_params)
            if not isinstance(payload, list) or not payload:
                break
            pages.append(payload)
            if len(payload) < GITHUB_PAGE_SIZE:
                break
            page_number += 1
        return pages

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.api_base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
        except requests.RequestException as exc:
            raise GitHubAPIError(f"GitHub request failed: {exc}") from exc

        if response.status_code >= 400:
            message = _extract_error_message(response)
            raise GitHubAPIError(f"GitHub API error {response.status_code}: {message}", response.status_code)

        if response.status_code == 204 or not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError("GitHub returned a non-JSON response") from exc


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:ERROR_BODY_PREVIEW_CHARS]
    message = payload.get("message", "Unknown error")
    errors = payload.get("errors")
    if errors:
        return f"{message}; details={errors}"
    return message
