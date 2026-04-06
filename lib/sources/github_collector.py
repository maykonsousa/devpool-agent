import logging
from typing import Any, Optional

import httpx

from lib.config import GITHUB_REPOS, GITHUB_TOKEN, MAX_ITEMS_PER_SOURCE, REQUEST_TIMEOUT
from lib.parser.claude_parser import parse_job_posting

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def collect(lookups: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Coleta vagas de issues abertas em repos GitHub."""
    positions = []

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    for repo in GITHUB_REPOS:
        try:
            items = _collect_repo_issues(repo, headers, lookups)
            positions.extend(items)
            logger.info("Repo %s: %d vagas coletadas", repo, len(items))
        except Exception as e:
            logger.error("Erro ao coletar %s: %s", repo, str(e))

    return positions


def _collect_repo_issues(
    repo: str, headers: dict, lookups: Optional[dict] = None
) -> list[dict[str, Any]]:
    """Coleta issues abertas de um repo como vagas."""
    url = f"{GITHUB_API}/repos/{repo}/issues"
    params = {
        "state": "open",
        "sort": "created",
        "direction": "desc",
        "per_page": min(MAX_ITEMS_PER_SOURCE, 30),
    }

    response = httpx.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    issues = response.json()

    positions = []
    for issue in issues:
        if issue.get("pull_request"):
            continue

        title = issue.get("title", "")
        body = issue.get("body", "")
        labels = [label["name"] for label in issue.get("labels", [])]
        issue_number = issue.get("number", "")
        source_url = issue.get("html_url", "")

        raw_text = (
            f"Título: {title}\n"
            f"Labels: {', '.join(labels)}\n\n"
            f"{body[:3000]}"
        )

        parsed = parse_job_posting(
            raw_text=raw_text,
            source=f"github-{repo.replace('/', '-')}",
            identifier=str(issue_number),
            source_url=source_url,
            lookups=lookups,
        )

        if parsed:
            positions.append(parsed)

    return positions
