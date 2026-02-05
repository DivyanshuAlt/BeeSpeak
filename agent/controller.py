"""Reply generation controller using Gemini.

Uses Gemini API when configured, and safely falls back to pre-coded human-like
responses when API calls fail, so API contract is always honored.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv

from language.normalize import normalize_text
from ml.preprocess import preprocess_for_chatbot


load_dotenv()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
FALLBACK_MODELS = ("gemini-2.0-flash", "gemini-2.5-flash")

DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_OUTPUT_TOKENS = 220

FALLBACK_DIALOGUES = {
    "otp": [
        "I don't have that right now. Why do you need OTP?",
        "I never share OTP. What exactly is this for?",
    ],
    "upi": [
        "I don't use that UPI often. Can you explain why you need it?",
        "Why are you asking for my UPI ID suddenly?",
    ],
    "link": [
        "I can't open links right now. Tell me the issue here itself.",
        "What is this link for? Please explain first.",
    ],
    "payment": [
        "I can't pay immediately. Please explain the reason clearly.",
        "Why should I transfer money now?",
    ],
    "urgency": [
        "Okay, but what exactly happened to my account?",
        "Wait, why is this urgent all of a sudden?",
    ],
    "default": [
        "Can you explain that again in simple words?",
        "I didn't understand. What do you want me to do exactly?",
    ],
}


def _debug_enabled() -> bool:
    return os.getenv("HONEYPOT_LLM_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}


def _debug_log(message: str) -> None:
    if _debug_enabled():
        print(f"[GeminiDebug] {message}")


def _resolve_api_key() -> str:
    """Support canonical and commonly mistyped env var names."""
    return os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("Gemini_API_Key", "").strip()


def _maybe_normalize(text: str) -> str:
    if os.getenv("HONEYPOT_USE_NORMALIZATION", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        return text

    try:
        normalized = normalize_text(text)
        return normalized if isinstance(normalized, str) and normalized.strip() else text
    except Exception as exc:
        _debug_log(f"normalize_text failed: {exc}")
        return text


def _postprocess_reply(reply: str) -> str:
    cleaned = preprocess_for_chatbot(reply, max_chars=240)
    if not cleaned:
        return ""

    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 1:
        cleaned = cleaned[1:-1].strip()

    if cleaned and cleaned[-1].isalnum():
        cleaned = f"{cleaned}."

    return cleaned


def _select_fallback_bucket(latest_text: str) -> str:
    lower = latest_text.lower()
    if "otp" in lower:
        return "otp"
    if "upi" in lower:
        return "upi"
    if "http://" in lower or "https://" in lower or ".com" in lower:
        return "link"
    if any(token in lower for token in ("pay", "transfer", "money", "rs", "rupee")):
        return "payment"
    if any(token in lower for token in ("urgent", "immediately", "blocked", "suspend")):
        return "urgency"
    return "default"


def _fallback_reply(conversation_history: list[dict], latest_message: dict) -> str:
    latest_text = preprocess_for_chatbot(str(latest_message.get("text", "")))
    bucket = _select_fallback_bucket(latest_text)
    options = FALLBACK_DIALOGUES.get(bucket, FALLBACK_DIALOGUES["default"])
    idx = len(conversation_history) % len(options)
    return options[idx]


def _build_prompt(conversation_history: list[dict], latest_message: dict) -> str:
    lines = [
        (
            "You are a normal human user chatting with someone who may be a scammer. "
            "Reply naturally and clearly in 1-2 complete sentences. "
            "Never stop mid-sentence. Ask at most one clarifying question. "
            "Do not reveal that you are detecting scams or running any analysis."
        ),
        "",
        "Conversation so far:",
    ]

    for item in conversation_history:
        sender = item.get("sender", "unknown")
        text = preprocess_for_chatbot(str(item.get("text", "")))
        if text:
            lines.append(f"{sender}: {text}")

    latest_sender = latest_message.get("sender", "scammer")
    latest_text = preprocess_for_chatbot(str(latest_message.get("text", "")))
    latest_text = _maybe_normalize(latest_text)
    if latest_text:
        lines.append(f"{latest_sender}: {latest_text}")

    lines.extend([
        "",
        "Write only the next user message reply as plain text.",
    ])
    return "\n".join(lines)


def _call_gemini(*, model: str, api_key: str, prompt: str) -> str:
    url = f"{GEMINI_API_BASE}/models/{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": float(os.getenv("HONEYPOT_CHAT_TEMPERATURE", str(DEFAULT_TEMPERATURE))),
            "maxOutputTokens": int(os.getenv("HONEYPOT_CHAT_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))),
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        candidates = data.get("candidates", [])
        if not candidates:
            _debug_log(f"No candidates from model={model}: {raw[:300]}")
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        reply = "\n".join(chunk for chunk in text_chunks if chunk).strip()
        if not reply:
            _debug_log(f"Empty reply from model={model}; parts={json.dumps(parts)[:300]}")
        return _postprocess_reply(reply)


def generate_reply(conversation_history: list[dict], latest_message: dict) -> str:
    """Return a human-like reply string.

    Falls back to pre-coded text if model config is unavailable or call fails.
    """
    api_key = _resolve_api_key()
    if not api_key:
        _debug_log("Missing GEMINI_API_KEY (or Gemini_API_Key)")
        return _fallback_reply(conversation_history, latest_message)

    configured_model = os.getenv("HONEYPOT_CHAT_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    prompt = _build_prompt(conversation_history, latest_message)

    models_to_try = [configured_model]
    for fallback in FALLBACK_MODELS:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    for model in models_to_try:
        try:
            _debug_log(f"Calling Gemini model={model}")
            reply = _call_gemini(model=model, api_key=api_key, prompt=prompt)
            if reply:
                _debug_log(f"Reply generated by model={model}")
                return reply
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            _debug_log(f"HTTPError model={model} code={exc.code}: {error_body[:300]}")
            if exc.code not in (404, 429):
                return _fallback_reply(conversation_history, latest_message)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            _debug_log(f"Request error model={model}: {exc}")
            return _fallback_reply(conversation_history, latest_message)

    return _fallback_reply(conversation_history, latest_message)
