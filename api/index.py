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
            "/api/cron-linkedin": self._cron_linkedin,
            "/api/debug": self._debug,
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

    def _debug(self):
        import httpx
        from lib.publisher.lookups_client import get_lookups
        from lib.parser.claude_parser import parse_job_posting
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)
            lookups_info = {
                "roles": len(lookups.get("roles", [])),
                "technologies": len(lookups.get("technologies", [])),
                "positionTypes": lookups.get("positionTypes", []),
                "positionModels": lookups.get("positionModels", []),
            }

            # Pegar 1 issue
            resp = httpx.get(
                "https://api.github.com/repos/frontendbr/vagas/issues",
                headers={"Accept": "application/vnd.github.v3+json"},
                params={"state": "open", "per_page": 1},
                timeout=15,
            )
            issues = resp.json()
            issue = issues[0]
            title = issue.get("title", "")
            body = issue.get("body", "")[:2000]
            labels = [l["name"] for l in issue.get("labels", [])]

            raw_text = f"Título: {title}\nLabels: {', '.join(labels)}\n\n{body}"

            parsed = parse_job_posting(
                raw_text=raw_text,
                source="debug",
                identifier=str(issue["number"]),
                source_url=issue.get("html_url", ""),
                lookups=lookups,
            )

            self._json_response(200, {
                "lookups": lookups_info,
                "issue": {"number": issue["number"], "title": title},
                "raw_text_length": len(raw_text),
                "parsed": parsed,
            })
        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _cron_linkedin(self):
        from lib.sources.google_linkedin_collector import collect
        from lib.publisher.devpool_client import publish_positions
        from lib.publisher.lookups_client import get_lookups
        from lib.config import DEVPOOL_API_URL

        try:
            lookups = get_lookups(DEVPOOL_API_URL)
            positions = collect(lookups=lookups)
            result = publish_positions(positions)
            self._json_response(200, {
                "status": "success",
                "source": "linkedin",
                "summary": {
                    "collected": len(positions),
                    "created": result["created"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
                "results": result.get("results", []),
            })
        except Exception as e:
            logger.error("Erro cron LinkedIn: %s", str(e))
            self._json_response(500, {"status": "error", "message": str(e)})

    def _not_found(self):
        self._json_response(404, {"status": "error", "message": "Route not found"})

    def _json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
