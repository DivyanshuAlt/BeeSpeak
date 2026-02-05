# core/decision.py

from core.settings import ML_SCAM_THRESHOLD


def decide(rule_result, ml_result=None):
    if rule_result["status"] == "CONFIRMED_SCAM":
        return {
            "is_scam": True,
            "decision_source": "rule",
            "confidence": rule_result["confidence"],
            "category": rule_result["primary_category"],
            "keywords": rule_result["matched_keywords"]
        }

    if ml_result and ml_result["scam_probability"] >= ML_SCAM_THRESHOLD:
        return {
            "is_scam": True,
            "decision_source": "ml",
            "confidence": ml_result["scam_probability"],
            "category": "ML_DETECTED",
            "keywords": []
        }

    return {
        "is_scam": False,
        "decision_source": "ml",
        "confidence": ml_result["scam_probability"] if ml_result else 0.0,
        "category": None,
        "keywords": []
    }
