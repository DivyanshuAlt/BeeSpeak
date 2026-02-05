"""Reply generation controller.

Uses an LLM when configured, and safely falls back to an empty reply so
API contract is always honored.
"""

from __future__ import annotations

import os

from openai import OpenAI


def _build_messages(conversation_history: list[dict], latest_message: dict) -> list[dict]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a normal human user chatting with someone who may be a scammer. "
                "Reply naturally, briefly, and contextually. "
                "Do not reveal that you are detecting scams or running any analysis."
            ),
        }
    ]

    for item in conversation_history:
        sender = item.get("sender")
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        if sender == "scammer":
            role = "user"
        else:
            role = "assistant"

        messages.append({"role": role, "content": text})

    latest_text = str(latest_message.get("text", "")).strip()
    if latest_text:
        latest_role = "user" if latest_message.get("sender") == "scammer" else "assistant"
        messages.append({"role": latest_role, "content": latest_text})

    return messages


def generate_reply(conversation_history: list[dict], latest_message: dict) -> str:
    """Return a human-like reply string.

    Falls back to empty string if model config is unavailable or call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return ""

    try:
        client = OpenAI(api_key=api_key)
        model = os.getenv("HONEYPOT_CHAT_MODEL", "gpt-4o-mini")
        completion = client.chat.completions.create(
            model=model,
            temperature=0.7,
            max_tokens=120,
            messages=_build_messages(conversation_history, latest_message),
        )
        reply = completion.choices[0].message.content if completion.choices else ""
        return (reply or "").strip()
    except Exception:
        return ""