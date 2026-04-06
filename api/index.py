from http.server import BaseHTTPRequestHandler
import json
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        routes = {
            "/api": self._health,
            "/api/health": self._health,
            "/api/cron-rss": self._cron_rss,
            "/api/cron-github": self._cron_github,
            "/api/cron-scraper": self._cron_scraper,
        }

        route_handler = routes.get(path, self._not_found)
        route_handler()

    def _health(self):
        self._json_response(200, {"status": "ok", "service": "devpool-agent"})

    def _cron_rss(self):
        from lib.sources.rss_collector import collect
        from lib.publisher.devpool_client import publish_positions
        from lib.publisher.lookups_client import get_lookups
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)
            positions = collect(lookups=lookups)
            result = publish_positions(positions)
            self._json_response(200, {
                "status": "success",
                "source": "rss",
                "summary": {
                    "collected": len(positions),
                    "created": result["created"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            })
        except Exception as e:
            logger.error("Erro cron RSS: %s", str(e))
            self._json_response(500, {"status": "error", "message": str(e)})

    def _cron_github(self):
        from lib.sources.github_collector import collect
        from lib.publisher.devpool_client import publish_positions
        from lib.publisher.lookups_client import get_lookups
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)
            positions = collect(lookups=lookups)
            result = publish_positions(positions)
            self._json_response(200, {
                "status": "success",
                "source": "github",
                "summary": {
                    "collected": len(positions),
                    "created": result["created"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
                "results": result.get("results", []),
            })
        except Exception as e:
            logger.error("Erro cron GitHub: %s", str(e))
            self._json_response(500, {"status": "error", "message": str(e)})

    def _cron_scraper(self):
        from lib.sources.web_scraper import collect
        from lib.publisher.devpool_client import publish_positions
        from lib.publisher.lookups_client import get_lookups
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)
            positions = collect(lookups=lookups)
            result = publish_positions(positions)
            self._json_response(200, {
                "status": "success",
                "source": "scraper",
                "summary": {
                    "collected": len(positions),
                    "created": result["created"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            })
        except Exception as e:
            logger.error("Erro cron Scraper: %s", str(e))
            self._json_response(500, {"status": "error", "message": str(e)})

    def _not_found(self):
        self._json_response(404, {"status": "error", "message": "Route not found"})

    def _json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
