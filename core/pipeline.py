from __future__ import annotations

from agent.controller import generate_reply
from core.decision import decide
from core.final_callback import send_final_callback_if_needed
from core.info_extractor import extract_entities
from core.session_storage import clear_session_state, store_turn
from language.normalize import normalize_text
from ml.classifier import predict as ml_predict
from rules.rule_engine import check as rule_check
from schemas.response_schema import base_response

VALID_SENDERS = {"scammer", "user"}


def _validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    session_id = payload.get("sessionId")
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("sessionId must be a non-empty string")

    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("message must be an object")

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("message.text must be a non-empty string")

    conversation_history = payload.get("conversationHistory")
    if conversation_history is None:
        payload["conversationHistory"] = []
        conversation_history = payload["conversationHistory"]
    if not isinstance(conversation_history, list):
        raise ValueError("conversationHistory must be an array")

    for entry in conversation_history:
        _validate_history_entry(entry)

    _validate_and_extract_metadata(payload)


def _validate_history_entry(message: dict) -> None:
    if not isinstance(message, dict):
        raise ValueError("conversationHistory entries must be objects")

    sender = message.get("sender")
    text = message.get("text")
    if sender not in VALID_SENDERS:
        raise ValueError("conversationHistory.sender must be 'scammer' or 'user'")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("conversationHistory.text must be a non-empty string")


def _validate_and_extract_metadata(payload: dict) -> dict[str, str]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    validated: dict[str, str] = {}
    for field_name in ("channel", "language", "locale"):
        value = metadata.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"metadata.{field_name} must be a non-empty string")
        validated[field_name] = value

    return validated


def _prepare_rule_text(raw_text: str) -> str:
    return raw_text.strip().lower()


def _prepare_ml_text(raw_text: str) -> str:
    return normalize_text(raw_text)


def _build_agent_note(decision: dict, entities: dict) -> str:
    notes = []
    if decision.get("is_scam"):
        notes.append("Scam intent detected")

    if entities.get("upi_ids"):
        notes.append("UPI ID captured")
    if entities.get("phone_numbers"):
        notes.append("Phone number extracted")
    if entities.get("phishing_links"):
        notes.append("Phishing link observed")
    if entities.get("suspicious_keywords"):
        notes.append("Suspicious language present")

    return "; ".join(notes)


def process_message(payload: dict) -> dict:
    _validate_payload(payload)

    session_id = payload["sessionId"]
    message = payload["message"]
    conversation_history = payload.get("conversationHistory", [])
    metadata = _validate_and_extract_metadata(payload)
    text = message["text"]

    rule_result = rule_check(_prepare_rule_text(text))

    ml_result = None
    if rule_result["status"] == "PASS_TO_ML":
        ml_result = ml_predict(_prepare_ml_text(text), "en")

    decision = decide(rule_result, ml_result)

    context_text = "\n".join(
        f"{entry['sender']}: {entry['text']}" for entry in conversation_history if entry.get("text")
    )
    entities = extract_entities(text, context_text)
    agent_note = _build_agent_note(decision, entities)

    session_state = store_turn(
        session_id=session_id,
        metadata=metadata,
        scam_confidence=decision["confidence"],
        is_scam=decision["is_scam"],
        extracted_indicators=entities,
    )

    reply = generate_reply(conversation_history, {"sender": "scammer", "text": text})

    callback_sent = send_final_callback_if_needed(
        session_id=session_id,
        is_scam=decision["is_scam"],
        extracted_entities=session_state.get("extractedIndicators", {}),
        agent_notes=agent_note,
        total_messages_exchanged=int(len(conversation_history) + 1),
    )
    if callback_sent:
        clear_session_state(session_id)

    response = base_response()
    response["reply"] = reply
    return response