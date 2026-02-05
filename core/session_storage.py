from __future__ import annotations

import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional


_SESSIONS: dict[str, dict] = {}
_TRANSIENT_CONTEXT: dict[str, dict] = {}
_CONTEXT_TTL_SECONDS = int(os.getenv("BEESPEAK_CONTEXT_TTL_SECONDS", "900"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_callback_state() -> dict:
    return {
        "sent": False,
        "sentAt": None,
        "idempotencyKey": None,
        "lastAttemptAt": None,
        "lastStatus": None,
    }


def _default_indicator_state() -> dict:
    return {
        "bank_accounts": [],
        "upi_ids": [],
        "phishing_links": [],
        "phone_numbers": [],
        "suspicious_keywords": [],
    }


def _default_session_state(session_id: str) -> dict:
    now = _utc_now_iso()
    return {
        "sessionId": session_id,
        "channel": "",
        "language": "",
        "locale": "",
        "createdAt": now,
        "updatedAt": now,
        "turnCount": 0,
        "latestScamConfidence": 0.0,
        "latestScamDetected": False,
        "extractedIndicators": _default_indicator_state(),
        "finalCallback": _default_callback_state(),
    }


def _merge_unique(target: list, incoming: Optional[list]):
    if not incoming:
        return
    for item in incoming:
        if item not in target:
            target.append(item)


def _cleanup_expired_context() -> None:
    now = time.time()
    expired = [
        session_id
        for session_id, value in _TRANSIENT_CONTEXT.items()
        if value.get("expiresAt", 0) <= now
    ]
    for session_id in expired:
        _TRANSIENT_CONTEXT.pop(session_id, None)


def get_transient_history(session_id: str) -> list:
    _cleanup_expired_context()
    context = _TRANSIENT_CONTEXT.get(session_id)
    if not context:
        return []
    return deepcopy(context.get("history", []))


def set_transient_history(session_id: str, history: list) -> None:
    _cleanup_expired_context()
    _TRANSIENT_CONTEXT[session_id] = {
        "history": deepcopy(history),
        "expiresAt": time.time() + max(_CONTEXT_TTL_SECONDS, 1),
    }


def clear_transient_history(session_id: str) -> None:
    _TRANSIENT_CONTEXT.pop(session_id, None)


def store_turn(
    session_id: str,
    metadata: dict,
    scam_confidence: float,
    is_scam: bool,
    extracted_indicators: dict,
) -> dict:
    """Persist/update minimal per-session state needed for callback decisions."""
    session_state = _SESSIONS.setdefault(session_id, _default_session_state(session_id))

    session_state["channel"] = metadata["channel"]
    session_state["language"] = metadata["language"]
    session_state["locale"] = metadata["locale"]
    session_state["updatedAt"] = _utc_now_iso()
    session_state["turnCount"] = int(session_state.get("turnCount", 0)) + 1
    session_state["latestScamConfidence"] = float(scam_confidence)
    session_state["latestScamDetected"] = bool(is_scam)

    indicators = session_state.setdefault("extractedIndicators", _default_indicator_state())
    incoming_indicators = extracted_indicators or {}
    for key in _default_indicator_state().keys():
        bucket = indicators.setdefault(key, [])
        _merge_unique(bucket, incoming_indicators.get(key, []))

    callback = session_state.setdefault("finalCallback", _default_callback_state())
    callback.setdefault("sent", False)
    callback.setdefault("sentAt", None)
    callback.setdefault("idempotencyKey", None)
    callback.setdefault("lastAttemptAt", None)
    callback.setdefault("lastStatus", None)

    return deepcopy(session_state)


def get_callback_status(session_id: str) -> dict:
    session_state = _SESSIONS.setdefault(session_id, _default_session_state(session_id))
    callback = session_state.setdefault("finalCallback", _default_callback_state())
    return deepcopy(callback)


def update_callback_status(session_id: str, **kwargs) -> dict:
    session_state = _SESSIONS.setdefault(session_id, _default_session_state(session_id))
    callback = session_state.setdefault("finalCallback", _default_callback_state())

    callback.update(kwargs)
    session_state["updatedAt"] = _utc_now_iso()
    return deepcopy(callback)


def get_session_state(session_id: str):
    state = _SESSIONS.get(session_id)
    if state is None:
        return None
    return deepcopy(state)


def clear_session_state(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
    _TRANSIENT_CONTEXT.pop(session_id, None)