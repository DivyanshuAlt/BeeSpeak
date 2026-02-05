# schemas/request_schema.py

"""Public wire contract for incoming requests to /api/process."""

REQUEST_SCHEMA = {
    "sessionId": str,
    "message": {
        "text": str,
    },
    "conversationHistory": [
        {
            "sender": str,
            "text": str,
        }
    ],
    "metadata": {
        "channel": str,
        "language": str,
        "locale": str,
    },
}