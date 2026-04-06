import logging
from typing import Any, Optional

import httpx

from lib.config import DEVPOOL_API_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_cache: Optional[dict[str, Any]] = None


def get_lookups(base_url: str) -> dict[str, Any]:
    """Busca valores válidos do DevPool. Cacheia em memória durante a execução."""
    global _cache
    if _cache is not None:
        return _cache

    lookups_url = base_url.replace("/ingestion/positions", "/ingestion/lookups")

    response = httpx.get(
        lookups_url,
        headers={"Authorization": f"Bearer {DEVPOOL_API_KEY}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "success":
        logger.error("Erro ao buscar lookups: %s", data)
        return {}

    _cache = data["data"]
    logger.info(
        "Lookups carregados: %d roles, %d techs, %d types, %d models",
        len(_cache.get("roles", [])),
        len(_cache.get("technologies", [])),
        len(_cache.get("positionTypes", [])),
        len(_cache.get("positionModels", [])),
    )
    return _cache


def setup_agent_user(base_url: str) -> Optional[str]:
    """Cria o usuário DevPool Agent se não existir. Retorna o agentUserId."""
    setup_url = base_url.replace("/ingestion/positions", "/ingestion/setup")

    response = httpx.post(
        setup_url,
        headers={"Authorization": f"Bearer {DEVPOOL_API_KEY}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "success":
        logger.info("Agent user: %s (%s)", data["username"], data["agentUserId"])
        return data["agentUserId"]

    logger.error("Erro ao criar agent user: %s", data)
    return None
