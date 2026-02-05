"""Rule-based entity and keyword extraction for scam intelligence."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from core.settings import SUSPICIOUS_TERMS
from rules.keyword_rules import KEYWORD_CATEGORIES

UPI_REGEX = re.compile(r"\b[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}\b")
PHONE_REGEX = re.compile(r"(?:\+91[\s-]?|0[\s-]?)?[6-9]\d(?:[\s-]?\d){8}")
URL_REGEX = re.compile(r"\bhttps?://[^\s<>()\[\]{}]+", re.IGNORECASE)
BARE_DOMAIN_REGEX = re.compile(
    r"\b(?:www\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:/[\w\-./?%&=+#]*)?\b",
    re.IGNORECASE,
)
BANK_ACCOUNT_REGEX = re.compile(r"\b\d{9,18}\b")
TRAILING_PUNCTUATION = ".,;:!?)]}>'\""


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output

def _normalize_phone(raw_phone: str) -> str | None:
    digits = re.sub(r"\D", "", raw_phone)

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) != 10 or digits[0] not in "6789":
        return None

    return f"+91{digits}"


def _normalize_url(raw_url: str) -> str:
    cleaned = raw_url.strip().rstrip(TRAILING_PUNCTUATION)
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = f"http://{cleaned}"

    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def _flatten_rule_keywords() -> list[str]:
    keywords = []
    for category_keywords in KEYWORD_CATEGORIES.values():
        keywords.extend(category_keywords)
    return keywords


def _extract_suspicious_keywords(text: str, custom_terms: list[str] | None = None) -> list[str]:
    lowered_text = text.lower()
    keyword_pool = _flatten_rule_keywords() + (custom_terms or SUSPICIOUS_TERMS)

    matches = []
    for keyword in keyword_pool:
        normalized_keyword = keyword.strip().lower()
        if normalized_keyword and normalized_keyword in lowered_text:
            matches.append(normalized_keyword)

    return _dedupe_preserve_order(matches)


def extract_entities(text: str, conversation_text: str = "", custom_terms: list[str] | None = None) -> dict:
    combined_text = f"{conversation_text}\n{text}".strip()

    upi_ids = _dedupe_preserve_order([match.lower() for match in UPI_REGEX.findall(combined_text)])

    phones = []
    for raw_phone in PHONE_REGEX.findall(combined_text):
        normalized_phone = _normalize_phone(raw_phone)
        if normalized_phone:
            phones.append(normalized_phone)
    phone_numbers = _dedupe_preserve_order(phones)

    urls = []
    explicit_url_spans = []
    for match in URL_REGEX.finditer(combined_text):
        explicit_url_spans.append((match.start(), match.end()))
        urls.append(_normalize_url(match.group(0)))

    for match in BARE_DOMAIN_REGEX.finditer(combined_text):
        start, end = match.span()
        if start > 0 and combined_text[start - 1] == "@":
            continue
        if end < len(combined_text) and combined_text[end:end + 1] == "@":
            continue
        if any(start >= s and end <= e for s, e in explicit_url_spans):
            continue
        urls.append(_normalize_url(match.group(0)))

    phishing_links = _dedupe_preserve_order(urls)
    suspicious_keywords = _extract_suspicious_keywords(combined_text, custom_terms)
    bank_accounts = _dedupe_preserve_order(BANK_ACCOUNT_REGEX.findall(combined_text))

    return {
        "bank_accounts": bank_accounts,
        "upi_ids": upi_ids,
        "phone_numbers": phone_numbers,
        "phishing_links": phishing_links,
        "suspicious_keywords": suspicious_keywords,
    }