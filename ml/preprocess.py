"""Text preprocessing helpers for reply-generation prompts."""

from __future__ import annotations

import re


def preprocess_for_chatbot(text: str, *, max_chars: int = 600) -> str:
    """Normalize whitespace and trim noisy long text for prompt stability."""
    cleaned = str(text or "")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if len(cleaned) > max_chars:
        cleaned = f"{cleaned[:max_chars].rstrip()}..."

    return cleaned
