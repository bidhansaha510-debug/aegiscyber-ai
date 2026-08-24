from __future__ import annotations

from typing import Any

import httpx

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.security.secrets import SecretsManager
from app.logging_config import get_logger

logger = get_logger("osint.connectors.github")


class GitHubConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "github"
    SUPPORTED_ENTITIES = [EntityType.ORGANIZATION, EntityType.USERNAME, EntityType.DOMAIN, EntityType.EMAIL]
    API_URL = "https://api.github.com"

    def __init__(self, secrets_manager: SecretsManager | None = None) -> None:
        self._secrets = secrets_manager
        self._token: str = ""
        if self._secrets:
            self._token = self._secrets.get_secret("github_token") or ""

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                if entity_type == EntityType.ORGANIZATION:
                    results.extend(await self._search_org(client, value))
                elif entity_type == EntityType.USERNAME:
                    results.extend(await self._search_user(client, value))
                elif entity_type == EntityType.DOMAIN:
                    results.extend(await self._search_code(client, value))
                elif entity_type == EntityType.EMAIL:
                    results.extend(await self._search_commits(client, value))
        except Exception as e:
            logger.error("GitHub search failed for %s: %s", value, e)

        return results

    async def _search_org(self, client: httpx.AsyncClient, org: str) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        response = await client.get(f"{self.API_URL}/orgs/{org}")
        if response.status_code == 200:
            data = response.json()
            results.append(OSINTResult(
                source="github",
                entity_type="organization",
                value=org,
                confidence=0.95,
                evidence=f"GitHub organization profile for {org}",
                raw_data={
                    "name": data.get("name", ""),
                    "blog": data.get("blog", ""),
                    "location": data.get("location", ""),
                    "public_repos": data.get("public_repos", 0),
                    "public_members": data.get("public_members_url", ""),
                },
            ))

        repos_response = await client.get(f"{self.API_URL}/orgs/{org}/repos?per_page=30&sort=updated")
        if repos_response.status_code == 200:
            repos = repos_response.json()
            for repo in repos:
                results.append(OSINTResult(
                    source="github",
                    entity_type="url",
                    value=repo.get("html_url", ""),
                    confidence=0.95,
                    evidence=f"Public repository in {org}",
                    raw_data={
                        "name": repo.get("name", ""),
                        "language": repo.get("language", ""),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                    },
                    relationships=[{"type": "associated_with", "from": org, "to": repo.get("html_url", "")}],
                ))

        return results

    async def _search_user(self, client: httpx.AsyncClient, username: str) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        response = await client.get(f"{self.API_URL}/users/{username}")
        if response.status_code == 200:
            data = response.json()
            results.append(OSINTResult(
                source="github",
                entity_type="username",
                value=username,
                confidence=0.95,
                evidence=f"GitHub user profile for {username}",
                raw_data={
                    "name": data.get("name", ""),
                    "company": data.get("company", ""),
                    "blog": data.get("blog", ""),
                    "location": data.get("location", ""),
                    "email": data.get("email", ""),
                    "bio": data.get("bio", ""),
                    "public_repos": data.get("public_repos", 0),
                },
            ))
        return results

    async def _search_code(self, client: httpx.AsyncClient, domain: str) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        response = await client.get(f"{self.API_URL}/search/code?q={domain}&per_page=10")
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", [])[:10]:
                results.append(OSINTResult(
                    source="github",
                    entity_type="url",
                    value=item.get("html_url", ""),
                    confidence=0.7,
                    evidence=f"Code reference to {domain}",
                    raw_data={
                        "repository": item.get("repository", {}).get("full_name", ""),
                        "path": item.get("path", ""),
                    },
                ))
        return results

    async def _search_commits(self, client: httpx.AsyncClient, email: str) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        response = await client.get(f"{self.API_URL}/search/commits?q=author-email:{email}&per_page=5")
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", [])[:5]:
                author = item.get("author", {}) or {}
                results.append(OSINTResult(
                    source="github",
                    entity_type="email",
                    value=email,
                    confidence=0.85,
                    evidence=f"Commit by {email}",
                    raw_data={
                        "repository": item.get("repository", {}).get("full_name", ""),
                        "author_login": author.get("login", ""),
                    },
                    relationships=[{
                        "type": "has_username",
                        "from": email,
                        "to": author.get("login", ""),
                    }] if author.get("login") else [],
                ))
        return results

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.API_URL}/rate_limit")
                return response.status_code in (200, 403)
        except Exception:
            return False
