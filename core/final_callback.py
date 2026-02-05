from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from core.session_storage import get_callback_status, update_callback_status

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
TIMEOUT_SECONDS = 5
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_idempotency_key(session_id: str) -> str:
    return f"final-result:{session_id}"


def should_trigger_final_callback(*, is_scam: bool, extracted_entities: dict, total_messages_exchanged: int) -> bool:
    """
    Explicit completion criteria:
      1) Scam intent is confirmed.
      2) Engagement is complete once at least one intelligence artifact has been extracted
         and at least 3 messages were exchanged in total.
    """
    if not is_scam:
        return False

    if total_messages_exchanged < 3:
        return False

    for key in ("bank_accounts", "upi_ids", "phishing_links", "phone_numbers", "suspicious_keywords"):
        if extracted_entities.get(key):
            return True

    return False


def _post_with_retries(payload: dict, idempotency_key: str) -> tuple[bool, str]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CALLBACK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
        },
        method="POST",
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.getcode()
                response_body = response.read().decode("utf-8", errors="replace")
                if 200 <= status < 300:
                    logger.info(
                        "Final callback success (attempt=%s, status=%s, sessionId=%s)",
                        attempt,
                        status,
                        payload.get("sessionId"),
                    )
                    return True, f"HTTP {status}: {response_body}"

                logger.warning(
                    "Final callback non-2xx (attempt=%s, status=%s, sessionId=%s)",
                    attempt,
                    status,
                    payload.get("sessionId"),
                )
                message = f"HTTP {status}: {response_body}"
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Final callback HTTPError (attempt=%s, status=%s, sessionId=%s)",
                attempt,
                exc.code,
                payload.get("sessionId"),
            )
            message = f"HTTPError {exc.code}: {error_body}"
        except urllib.error.URLError as exc:
            logger.warning(
                "Final callback URLError (attempt=%s, sessionId=%s, error=%s)",
                attempt,
                payload.get("sessionId"),
                str(exc),
            )
            message = f"URLError: {exc}"
        except TimeoutError as exc:
            logger.warning(
                "Final callback timeout (attempt=%s, sessionId=%s)",
                attempt,
                payload.get("sessionId"),
            )
            message = f"TimeoutError: {exc}"

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    logger.error("Final callback failed after retries (sessionId=%s)", payload.get("sessionId"))
    return False, message


def send_final_callback_if_needed(*, session_id: str, is_scam: bool, extracted_entities: dict, agent_notes: str, total_messages_exchanged: int) -> bool:
    callback_state = get_callback_status(session_id)
    if callback_state.get("sent"):
        logger.info("Final callback skipped; already sent (sessionId=%s)", session_id)
        return False

    if not should_trigger_final_callback(
        is_scam=is_scam,
        extracted_entities=extracted_entities,
        total_messages_exchanged=total_messages_exchanged,
    ):
        return False

    intelligence = {
        "bankAccounts": extracted_entities.get("bank_accounts", []),
        "upiIds": extracted_entities.get("upi_ids", []),
        "phishingLinks": extracted_entities.get("phishing_links", []),
        "phoneNumbers": extracted_entities.get("phone_numbers", []),
        "suspiciousKeywords": extracted_entities.get("suspicious_keywords", []),
    }

    idempotency_key = callback_state.get("idempotencyKey") or _build_idempotency_key(session_id)
    payload = {
        "sessionId": session_id,
        "scamDetected": bool(is_scam),
        "totalMessagesExchanged": int(total_messages_exchanged),
        "extractedIntelligence": intelligence,
        "agentNotes": agent_notes,
    }

    update_callback_status(
        session_id,
        idempotencyKey=idempotency_key,
        lastAttemptAt=_utc_now_iso(),
        lastStatus="attempted",
    )

    success, result_message = _post_with_retries(payload, idempotency_key)

    if success:
        update_callback_status(
            session_id,
            sent=True,
            sentAt=_utc_now_iso(),
            lastStatus=f"success: {result_message}",
        )
        return True

    update_callback_status(
        session_id,
        lastStatus=f"failed: {result_message}",
    )
    return False