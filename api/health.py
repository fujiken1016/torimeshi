# -*- coding: utf-8 -*-
import json
from http.server import BaseHTTPRequestHandler
from _lib import has_key, MODEL


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "model": MODEL, "has_key": has_key()}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
