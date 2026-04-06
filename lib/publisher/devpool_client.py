import httpx
import logging
from typing import Any, Optional

from lib.config import DEVPOOL_API_URL, DEVPOOL_API_KEY, BATCH_SIZE, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def publish_positions(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Publica vagas no DevPool via API de ingestão, em lotes."""
    if not positions:
        return {"total": 0, "created": 0, "skipped": 0, "errors": 0, "results": []}

    all_results = []
    total_created = 0
    total_skipped = 0
    total_errors = 0

    for i in range(0, len(positions), BATCH_SIZE):
        batch = positions[i : i + BATCH_SIZE]
        result = _send_batch(batch)

        if result:
            all_results.extend(result.get("results", []))
            summary = result.get("summary", {})
            total_created += summary.get("created", 0)
            total_skipped += summary.get("skipped", 0)
            total_errors += summary.get("errors", 0)

    return {
        "total": len(positions),
        "created": total_created,
        "skipped": total_skipped,
        "errors": total_errors,
        "results": all_results,
    }


def _send_batch(batch: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Envia um lote de vagas para a API de ingestão."""
    try:
        response = httpx.post(
            DEVPOOL_API_URL,
            json={"positions": batch},
            headers={
                "Authorization": f"Bearer {DEVPOOL_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 201:
            data = response.json()
            logger.info(
                "Lote enviado: %d criadas, %d duplicadas, %d erros",
                data.get("summary", {}).get("created", 0),
                data.get("summary", {}).get("skipped", 0),
                data.get("summary", {}).get("errors", 0),
            )
            return data

        logger.error(
            "Erro ao enviar lote: status=%d body=%s",
            response.status_code,
            response.text[:200],
        )
        return None

    except httpx.HTTPError as e:
        logger.error("Erro HTTP ao enviar lote: %s", str(e))
        return None
