import logging
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from lib.config import SCRAPER_SOURCES, MAX_ITEMS_PER_SOURCE, REQUEST_TIMEOUT
from lib.parser.claude_parser import parse_job_posting

logger = logging.getLogger(__name__)

USER_AGENT = "DevPool-Agent/1.0 (job aggregator; contact: contato@devpool.com.br)"


def collect(lookups: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Coleta vagas via scraping de sites configurados."""
    positions = []

    for source in SCRAPER_SOURCES:
        try:
            items = _scrape_source(source, lookups)
            positions.extend(items)
            logger.info("Scraper %s: %d vagas coletadas", source["name"], len(items))
        except Exception as e:
            logger.error("Erro ao fazer scraping de %s: %s", source["name"], str(e))

    return positions


def _scrape_source(source: dict, lookups: Optional[dict] = None) -> list[dict[str, Any]]:
    """Faz scraping de uma fonte específica."""
    response = httpx.get(
        source["url"],
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    elements = soup.select(source["selector"])[:MAX_ITEMS_PER_SOURCE]

    positions = []
    for i, element in enumerate(elements):
        raw_text = element.get_text(separator="\n", strip=True)
        if len(raw_text) < 20:
            continue

        link_tag = element.find("a", href=True)
        source_url = ""
        if link_tag:
            href = link_tag["href"]
            if href.startswith("/"):
                base = source["url"].split("/")[0:3]
                source_url = "/".join(base) + href
            else:
                source_url = href

        parsed = parse_job_posting(
            raw_text=raw_text,
            source=source["name"],
            identifier=source_url or f"{source['name']}-{i}",
            source_url=source_url or source["url"],
            lookups=lookups,
        )

        if parsed:
            positions.append(parsed)

    return positions
