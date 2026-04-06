import logging
from typing import Any, Optional

import feedparser
import httpx

from lib.config import RSS_FEEDS, MAX_ITEMS_PER_SOURCE, REQUEST_TIMEOUT
from lib.parser.claude_parser import parse_job_posting

logger = logging.getLogger(__name__)


def collect(lookups: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Coleta vagas de todas as fontes RSS/JSON configuradas."""
    positions = []

    for feed_config in RSS_FEEDS:
        try:
            if feed_config["type"] == "rss":
                items = _collect_rss(feed_config, lookups)
            elif feed_config["type"] == "json":
                items = _collect_json_api(feed_config, lookups)
            else:
                continue

            positions.extend(items)
            logger.info(
                "Fonte %s: %d vagas coletadas", feed_config["name"], len(items)
            )
        except Exception as e:
            logger.error("Erro ao coletar %s: %s", feed_config["name"], str(e))

    return positions


def _collect_rss(feed_config: dict, lookups: Optional[dict] = None) -> list[dict[str, Any]]:
    """Coleta vagas de um feed RSS."""
    feed = feedparser.parse(feed_config["url"])
    positions = []

    for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        raw_text = f"Título: {entry.get('title', '')}\n\n{entry.get('summary', entry.get('description', ''))}"
        source_url = entry.get("link", "")
        identifier = entry.get("id", entry.get("link", entry.get("title", "")))

        parsed = parse_job_posting(
            raw_text=raw_text,
            source=feed_config["name"],
            identifier=identifier,
            source_url=source_url,
            lookups=lookups,
        )

        if parsed:
            positions.append(parsed)

    return positions


def _collect_json_api(feed_config: dict, lookups: Optional[dict] = None) -> list[dict[str, Any]]:
    """Coleta vagas de uma API JSON (ex: Remotive)."""
    response = httpx.get(feed_config["url"], timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        return []

    positions = []
    for job in jobs[:MAX_ITEMS_PER_SOURCE]:
        raw_text = (
            f"Título: {job.get('title', '')}\n"
            f"Empresa: {job.get('company_name', '')}\n"
            f"Categoria: {job.get('category', '')}\n"
            f"Tags: {', '.join(job.get('tags', []))}\n\n"
            f"{job.get('description', '')}"
        )
        source_url = job.get("url", "")
        identifier = str(job.get("id", job.get("url", job.get("title", ""))))

        parsed = parse_job_posting(
            raw_text=raw_text,
            source=feed_config["name"],
            identifier=identifier,
            source_url=source_url,
            lookups=lookups,
        )

        if parsed:
            positions.append(parsed)

    return positions
