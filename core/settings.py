# core/settings.py

SCAM_RULE_CONFIDENCE = 0.95
ML_SCAM_THRESHOLD = 0.70

SUPPORTED_LANGUAGES = ["en", "hi", "ta"]

DEBUG = True

SUSPICIOUS_TERMS = [
    "otp",
    "kyc",
    "click link",
    "bank update",
]