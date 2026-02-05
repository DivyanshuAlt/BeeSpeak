"""Interactive terminal client for fake test center.

Run this in CMD B while fake_test_center_server.py runs in CMD A.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8787"
SESSION_ID = f"local-session-{int(time.time())}"


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    print(f"Connected to {BASE_URL}")
    print(f"sessionId={SESSION_ID}")
    print("Type scammer messages. Type 'exit' to stop and request final JSON.\n")

    while True:
        text = input("scammer> ").strip()
        if not text:
            continue

        if text.lower() in {"exit", "quit"}:
            try:
                final_result = _post("/done", {"sessionId": SESSION_ID})
                print("\nDone. Final JSON from server:")
                print(json.dumps(final_result.get("final", {}), indent=2, ensure_ascii=False))
            except urllib.error.URLError as exc:
                print(f"could not fetch final JSON from server: {exc}")
            break

        try:
            response = _post(
                "/chat",
                {
                    "sessionId": SESSION_ID,
                    "sender": "scammer",
                    "text": text,
                    "timestamp": int(time.time() * 1000),
                    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
                },
            )
        except urllib.error.URLError as exc:
            print(f"request failed: {exc}")
            continue

        print("honeypot>", response.get("reply", ""))
        print("raw>", json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()