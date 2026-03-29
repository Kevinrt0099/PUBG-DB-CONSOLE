"""REST API endpoints for serving player and match statistics."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from stats_service import StatsService
from stats_formatter import StatsFormatter


class StatsAPIHandler(BaseHTTPRequestHandler):
    service = StatsService()
    formatter = StatsFormatter()

    def do_GET(self):
        try:
            if self.path.startswith("/api/player/"):
                player_id = int(self.path.split("/")[-1])
                data = self.service.get_player_overview(player_id)
                if data:
                    self._json_response(200, self.formatter.format_player(data))
                else:
                    self._json_response(404, {"error": "Player not found"})

            elif self.path.startswith("/api/leaderboard"):
                metric = self._get_param("metric", "kills")
                limit = int(self._get_param("limit", "10"))
                data = self.service.get_leaderboard(metric=metric, limit=limit)
                self._json_response(200, self.formatter.format_leaderboard(data, metric))

            elif self.path == "/api/weapons/meta":
                data = self.service.get_weapon_meta()
                self._json_response(200, self.formatter.format_weapon_meta(data))

            elif self.path == "/api/cache/stats":
                self._json_response(200, self.service.cache.stats())

            else:
                self._json_response(404, {"error": "Endpoint not found"})

        except ValueError as e:
            self._json_response(400, {"error": str(e)})
        except Exception as e:
            self._json_response(500, {"error": "Internal server error"})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _get_param(self, name, default=None):
        if "?" not in self.path:
            return default
        params = dict(p.split("=") for p in self.path.split("?")[1].split("&") if "=" in p)
        return params.get(name, default)


def run_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), StatsAPIHandler)
    print(f"Stats API server running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
