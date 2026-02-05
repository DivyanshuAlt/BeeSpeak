# rules/rule_engine.py

from rules.keyword_rules import KEYWORD_CATEGORIES, CATEGORY_PRIORITY
from rules.url_rules import evaluate as evaluate_urls


def check(text: str):
    matched = {}

    for category, keywords in KEYWORD_CATEGORIES.items():
        hits = [kw for kw in keywords if kw in text]
        if hits:
            matched[category] = hits

    url_result = evaluate_urls(text)
    if url_result["suspicious_urls"]:
        matched.setdefault("PHISHING_LINK", []).extend(url_result["suspicious_urls"])

    if not matched:
        return {
            "status": "PASS_TO_ML",
            "url_analysis": url_result,
        }

    # pick primary category by priority
    primary_category = None
    for cat in CATEGORY_PRIORITY:
        if cat in matched:
            primary_category = cat
            break

    if primary_category is None and "PHISHING_LINK" in matched:
        primary_category = "PHISHING_LINK"

    # merge all keywords into one list (unique)
    all_keywords = []
    for kws in matched.values():
        all_keywords.extend(kws)

    all_keywords = list(set(all_keywords))  # remove duplicates

    return {
        "status": "CONFIRMED_SCAM",
        "confidence": 0.95,
        "primary_category": primary_category,
        "matched_keywords": all_keywords,
        "url_analysis": url_result,
    }