import logging
import random
import re
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from lib.config import (
    LINKEDIN_QUERIES_PER_RUN,
    LINKEDIN_RESULTS_PER_QUERY,
    REQUEST_TIMEOUT,
    generate_external_id,
)
from lib.parser.claude_parser import parse_job_posting

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SEARCH_TEMPLATES = [
    'site:linkedin.com/posts "{role}" ("vaga" OR "contratando" OR "oportunidade") ("email" OR "enviar currículo")',
    'site:linkedin.com/feed/update "{role}" ("vaga" OR "estamos contratando") ("email" OR "cv para")',
    'site:linkedin.com/posts "{role}" ("{tech}") ("remoto" OR "CLT" OR "PJ") "email"',
]


def collect(lookups: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Coleta vagas de posts do LinkedIn via Google Search."""
    if not lookups:
        logger.warning("Lookups não disponíveis, pulando coleta LinkedIn")
        return []

    roles = lookups.get("roles", [])
    techs = lookups.get("technologies", [])

    if not roles:
        return []

    selected_roles = random.sample(roles, min(LINKEDIN_QUERIES_PER_RUN, len(roles)))
    positions = []

    for role in selected_roles:
        try:
            tech = random.choice(techs) if techs else ""
            query = _build_query(role, tech)
            urls = _google_search(query)
            items = _process_urls(urls, role, lookups)
            positions.extend(items)
            logger.info("LinkedIn [%s]: %d vagas de %d URLs", role, len(items), len(urls))
        except Exception as e:
            logger.error("Erro ao buscar LinkedIn [%s]: %s", role, str(e))

    return positions


def _build_query(role: str, tech: str) -> str:
    """Monta query booleana para Google."""
    template = random.choice(SEARCH_TEMPLATES)
    return template.format(role=role, tech=tech)


def _google_search(query: str) -> list[str]:
    """Busca no Google e retorna URLs de posts do LinkedIn."""
    encoded = quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}&num={LINKEDIN_RESULTS_PER_QUERY}"

    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        links = []

        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            linkedin_urls = re.findall(
                r"https?://(?:www\.)?linkedin\.com/(?:posts|feed/update)/[^\s&\"]+",
                href,
            )
            links.extend(linkedin_urls)

        unique = list(dict.fromkeys(links))[:LINKEDIN_RESULTS_PER_QUERY]
        logger.info("Google: %d URLs LinkedIn encontradas para: %s", len(unique), query[:80])
        return unique

    except httpx.HTTPError as e:
        logger.error("Erro Google Search: %s", str(e))
        return []


def _process_urls(
    urls: list[str],
    role: str,
    lookups: dict[str, Any],
) -> list[dict[str, Any]]:
    """Acessa posts do LinkedIn e extrai vagas."""
    positions = []

    for url in urls:
        try:
            text = _fetch_linkedin_post(url)
            if not text or len(text) < 50:
                continue

            parsed = parse_job_posting(
                raw_text=text,
                source="linkedin",
                identifier=url,
                source_url=url,
                lookups=lookups,
            )

            if parsed:
                positions.append(parsed)

        except Exception as e:
            logger.error("Erro ao processar %s: %s", url[:80], str(e))

    return positions


def _fetch_linkedin_post(url: str) -> str:
    """Acessa um post público do LinkedIn e extrai o texto."""
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # LinkedIn public posts têm o conteúdo em diferentes seletores
        selectors = [
            "div.feed-shared-update-v2__description",
            "div.attributed-text-segment-list__container",
            "span.break-words",
            "div.update-components-text",
            "article",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    return text

        # Fallback: meta description
        meta = soup.find("meta", {"name": "description"}) or soup.find(
            "meta", {"property": "og:description"}
        )
        if meta and meta.get("content"):
            return meta["content"]

        return ""

    except httpx.HTTPError as e:
        logger.error("Erro ao acessar LinkedIn: %s", str(e))
        return ""
