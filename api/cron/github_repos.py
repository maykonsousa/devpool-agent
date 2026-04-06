from http.server import BaseHTTPRequestHandler
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from lib.sources.github_collector import collect
        from lib.publisher.devpool_client import publish_positions
        from lib.publisher.lookups_client import get_lookups
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)

            logger.info("Iniciando coleta GitHub repos...")
            positions = collect(lookups=lookups)
            logger.info("GitHub: %d vagas extraídas, publicando...", len(positions))

            result = publish_positions(positions)

            response = {
                "status": "success",
                "source": "github_repos",
                "summary": {
                    "collected": len(positions),
                    "created": result["created"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error("Erro no cron GitHub: %s", str(e))
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "error", "message": str(e)}).encode()
            )
