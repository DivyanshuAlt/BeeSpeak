# api/process.py

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
# Make project root importable
api_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(api_dir, os.pardir))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.pipeline import process_message

API_KEY = os.environ.get("HONEY_POT_API_KEY", "guvi-honeypot-2026")


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _authenticate(self):
        incoming_key = self.headers.get("x-api-key")

        if not incoming_key:
            self._send_json(401, {"error": "Missing x-api-key"})
            return False

        if incoming_key != API_KEY:
            self._send_json(401, {"error": "Invalid API key"})
            return False

        return True

    def do_GET(self):
        if not self._authenticate():
            return

        self._send_json(
            200,
            {
                "status": "SUCCESS",
                "service": "BeeSpeak Honeypot API",
            },
        )

    def do_POST(self):
        if not self._authenticate():
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body)
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        try:
            result = process_message(payload)
        except Exception as e:
            self._send_json(500, {"error": str(e)})
            return

        self._send_json(200, result)