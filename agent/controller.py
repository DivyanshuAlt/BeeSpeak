"""Reply generation controller using Gemini.

Uses Gemini API when configured, and safely falls back to an empty reply so
API contract is always honored.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _build_prompt(conversation_history: list[dict], latest_message: dict) -> str:
    lines = [
        (
            "You are a normal human user chatting with someone who may be a scammer. "
            "Reply naturally, briefly, and contextually. "
            "Do not reveal that you are detecting scams or running any analysis."
        ),
        "",
        "Conversation so far:",
    ]

    for item in conversation_history:
        sender = item.get("sender", "unknown")
        text = str(item.get("text", "")).strip()
        if text:
            lines.append(f"{sender}: {text}")

    latest_sender = latest_message.get("sender", "scammer")
    latest_text = str(latest_message.get("text", "")).strip()
    if latest_text:
        lines.append(f"{latest_sender}: {latest_text}")

    lines.extend(
        [
            "",
            "Write only the next user message reply as plain text.",
        ]
    )
    return "\n".join(lines)


def generate_reply(conversation_history: list[dict], latest_message: dict) -> str:
    """Return a human-like reply string.

    Falls back to empty string if model config is unavailable or call fails.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return ""

    model = os.getenv("HONEYPOT_CHAT_MODEL", "gemini-1.5-flash")
    prompt = _build_prompt(conversation_history, latest_message)

    url = f"{GEMINI_API_BASE}/models/{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 120,
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            candidates = data.get("candidates", [])
            if not candidates:
                return ""

            parts = candidates[0].get("content", {}).get("parts", [])
            text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
            return "\n".join(chunk for chunk in text_chunks if chunk).strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return ""
