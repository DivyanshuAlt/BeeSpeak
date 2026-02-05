"""Persistent conversation history storage keyed by session ID."""

import json
import os
from copy import deepcopy


_DEFAULT_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "conversation_store.json",
)
_STORE_PATH = os.getenv("BEESPEAK_STORE_PATH", _DEFAULT_STORE_PATH)
_MEMORY_STORE = {}


def _ensure_store_file():
    if not _STORE_PATH:
        return False

    try:
        os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
        if not os.path.exists(_STORE_PATH):
            with open(_STORE_PATH, "w", encoding="utf-8") as file:
                json.dump({}, file)
        return True
    except OSError:
        return False


def _read_store():
    if not _ensure_store_file():
        return deepcopy(_MEMORY_STORE)

    try:
        with open(_STORE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass

    return deepcopy(_MEMORY_STORE)


def _write_store(store_data):
    global _MEMORY_STORE
    if not _ensure_store_file():
        _MEMORY_STORE = deepcopy(store_data)
        return

    try:
        with open(_STORE_PATH, "w", encoding="utf-8") as file:
            json.dump(store_data, file, ensure_ascii=False)
    except OSError:
        _MEMORY_STORE = deepcopy(store_data)


def _validate_message_shape(message_obj):
    return (
        isinstance(message_obj, dict)
        and isinstance(message_obj.get("sender"), str)
        and isinstance(message_obj.get("text"), str)
        and isinstance(message_obj.get("timestamp"), int)
    )


def load_session(session_id):
    """Return the persisted message list for a session."""
    store_data = _read_store()
    session_messages = store_data.get(session_id, [])
    if not isinstance(session_messages, list):
        return []
    return deepcopy(session_messages)


def append_message(session_id, message_obj):
    """Append one validated message object to a session and persist."""
    if not _validate_message_shape(message_obj):
        raise ValueError("Message must include sender, text, and timestamp.")

    store_data = _read_store()
    session_messages = store_data.get(session_id, [])
    if not isinstance(session_messages, list):
        session_messages = []
    session_messages.append(message_obj)
    store_data[session_id] = session_messages
    _write_store(store_data)


def replace_session(session_id, messages):
    """Replace the full persisted history for a session and persist."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    for msg in messages:
        if not _validate_message_shape(msg):
            raise ValueError("Each message must include sender, text, and timestamp.")

    store_data = _read_store()
    store_data[session_id] = deepcopy(messages)
    _write_store(store_data)


def get_full_history(session_id):
    """Alias to load full history for consistency at call sites."""
    return load_session(session_id)