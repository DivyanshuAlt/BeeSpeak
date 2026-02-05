"""Small local server to verify final callback payload shape."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockCallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/updateHoneyPotFinalResult":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "invalid json"}).encode("utf-8"))
            return

        print("Received callback payload:")
        print(json.dumps(payload, indent=2))

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "message": "payload received"}).encode("utf-8"))


def run(host: str = "0.0.0.0", port: int = 8787) -> None:
    server = HTTPServer((host, port), MockCallbackHandler)
    print(f"Mock callback server running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
