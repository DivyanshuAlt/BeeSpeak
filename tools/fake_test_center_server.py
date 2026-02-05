"""Fake local test center server.

CMD A: run this server and watch logs.
CMD B: use tools/fake_test_center_client.py to send scammer messages interactively.
"""

import json
import os
import sys
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer

# Make project root importable when script is run from tools/
TOOLS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from core.pipeline import process_message
from core.session_storage import get_session_state

HISTORIES: dict[str, list[dict]] = {}
FINAL_CALLBACKS: dict[str, dict] = {}
DEFAULT_METADATA = {"channel": "SMS", "language": "English", "locale": "IN"}


def _pretty(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _build_final_preview(session_id: str) -> dict:
    state = get_session_state(session_id) or {}
    indicators = state.get("extractedIndicators", {})
    return {
        "sessionId": session_id,
        "scamDetected": bool(state.get("latestScamDetected", False)),
        "totalMessagesExchanged": int(state.get("turnCount", 0)),
        "extractedIntelligence": {
            "bankAccounts": indicators.get("bank_accounts", []),
            "upiIds": indicators.get("upi_ids", []),
            "phishingLinks": indicators.get("phishing_links", []),
            "phoneNumbers": indicators.get("phone_numbers", []),
            "suspiciousKeywords": indicators.get("suspicious_keywords", []),
        },
        "agentNotes": "(preview) built from in-memory session state",
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}

    def do_POST(self) -> None:
        try:
            body = self._read_json()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        if self.path == "/chat":
            self._handle_chat(body)
            return

        if self.path == "/final-callback":
            self._handle_final_callback(body)
            return

        if self.path == "/done":
            self._handle_done(body)
            return

        self._send_json(404, {"error": "unknown path"})

    def _handle_chat(self, body: dict) -> None:
        session_id = str(body.get("sessionId", "demo-session")).strip() or "demo-session"
        text = str(body.get("text", "")).strip()
        sender = str(body.get("sender", "scammer")).strip() or "scammer"
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else DEFAULT_METADATA

        if not text:
            self._send_json(400, {"error": "text is required"})
            return

        history = HISTORIES.setdefault(session_id, [])
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": sender,
                "text": text,
                "timestamp": body.get("timestamp", 0),
            },
            "conversationHistory": deepcopy(history),
            "metadata": metadata,
        }

        print("\n=== Incoming /chat payload ===")
        print(_pretty(payload))

        response = process_message(payload)

        history.append({"sender": sender, "text": text, "timestamp": body.get("timestamp", 0)})
        reply_text = str(response.get("reply", "")).strip()
        if reply_text:
            history.append({"sender": "user", "text": reply_text, "timestamp": body.get("timestamp", 0)})

        print("=== process_message response ===")
        print(_pretty(response))

        self._send_json(200, response)

    def _handle_final_callback(self, body: dict) -> None:
        session_id = str(body.get("sessionId", ""))
        if session_id:
            FINAL_CALLBACKS[session_id] = body

        print("\n=== FINAL CALLBACK RECEIVED ===")
        print(_pretty(body))

        self._send_json(200, {"ok": True, "message": "final callback captured"})

    def _handle_done(self, body: dict) -> None:
        session_id = str(body.get("sessionId", "demo-session")).strip() or "demo-session"

        final_payload = FINAL_CALLBACKS.get(session_id)
        if final_payload is None:
            final_payload = _build_final_preview(session_id)
            print("\n=== FINAL CALLBACK NOT RECEIVED YET (PREVIEW) ===")
        else:
            print("\n=== FINAL CALLBACK (FROM /final-callback) ===")

        print(_pretty(final_payload))

        self._send_json(200, {"status": "done", "sessionId": session_id, "final": final_payload})


def run(host: str = "0.0.0.0", port: int = 8787) -> None:
    server = HTTPServer((host, port), Handler)
    print(f"Fake test center server running at http://{host}:{port}")
    print("Use /chat from CMD B and set HONEYPOT_FINAL_CALLBACK_URL=http://localhost:8787/final-callback")
    server.serve_forever()


if __name__ == "__main__":
    run()
