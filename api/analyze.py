# -*- coding: utf-8 -*-
import json
from http.server import BaseHTTPRequestHandler
from _lib import analyze_image


class handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            out = analyze_image(payload.get("image", ""), payload.get("mode", "cut"))
            self._json(200, out)
        except RuntimeError as e:
            if str(e) == "no_api_key":
                self._json(503, {"error": "no_api_key", "message": "ANTHROPIC_API_KEY 未設定"})
            else:
                self._json(500, {"error": "server_error", "message": str(e)})
        except ValueError as e:
            self._json(400, {"error": "server_error", "message": str(e)})
        except Exception as e:
            self._json(500, {"error": "server_error", "message": str(e)})
